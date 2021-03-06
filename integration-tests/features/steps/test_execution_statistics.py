#!/usr/bin/env python
# -*- mode: python; coding: iso-8859-1 -*-

# SonarQube Python Plugin
# Copyright (C) Waleri Enns, Günter Wirth
# dev@sonar.codehaus.org

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02

import os
import re
import json
import requests
import platform
import sys
from   requests.auth import HTTPBasicAuth
import subprocess
import shutil
from behave import given, when, then, model
from common import analyselog, build_regexp, sonarlog, analyseloglines, ensureComputeEngineHasFinishedOk

RED = ""
YELLOW = ""
GREEN = ""
RESET = ""
RESET_ALL = ""
BRIGHT = ""
try:
    import colorama
    colorama.init()
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    GREEN = colorama.Fore.GREEN
    RESET = colorama.Fore.RESET
    BRIGHT = colorama.Style.BRIGHT
    RESET_ALL = colorama.Style.RESET_ALL
except ImportError:
    pass

TESTDATADIR = os.path.normpath(os.path.join(os.path.realpath(__file__),
                                            "..", "..", "..", "testdata"))
SONAR_URL = "http://localhost:9000"

TEST_METRICS_ORDER = [
    "tests",
    "test_failures",
    "test_errors",
    "skipped_tests",
    "test_success_density",
    "test_execution time"
    ]


@given(u'the project "{project}"')
def step_impl(context, project):
    assert os.path.isdir(os.path.join(TESTDATADIR, project))
    context.project = project
    context.profile_key = None
 
    url = (SONAR_URL + "/api/qualityprofiles/search")
    response = _restApiGet(url)
    profiles = _getJson(response)["profiles"]
    data = _gotKeyFromQualityProfile(profiles)
    default_profile_key = None
    for key, name in data.iteritems():
        if name == "Sonar way - c++":
            default_profile_key = key

    url = (SONAR_URL + "/api/qualityprofiles/set_default")
    payload = {'profileKey': default_profile_key}
    _restApiSet(url, payload)

    copy_profile_key = None
    for key, name in data.iteritems():
        if name == "Sonar way copy - c++":
            copy_profile_key = key

    if copy_profile_key:      
        url = (SONAR_URL + "/api/qualityprofiles/delete")
        payload = {'profileKey': copy_profile_key}
        _restApiSet(url, payload)
    
    url = (SONAR_URL + "/api/qualityprofiles/copy")
    payload = {'fromKey': default_profile_key, 'toName': 'Sonar way copy'}
    _restApiSet(url, payload)

    url = (SONAR_URL + "/api/qualityprofiles/search")
    response = _restApiGet(url)
    profiles = _getJson(response)["profiles"]
    data = _gotKeyFromQualityProfile(profiles)
    for key, name in data.iteritems():
        if name == "Sonar way copy - c++":
            context.profile_key = key

    url = (SONAR_URL + "/api/qualityprofiles/set_default")
    payload = {'profileKey': context.profile_key}
    _restApiSet(url, payload)

    
@given(u'platform is not "{plat}"')
def step_impl(context, plat):
    if platform.system() == plat:
        context.scenario.skip(reason='scenario meant to run only in specified platform')


@given(u'platform is "{plat}"')
def step_impl(context, plat):
    if platform.system() != plat:
        context.scenario.skip(reason='scenario meant to run only in specified platform')


@given(u'declared source extensions of language c++ are "{extensions}"')
def step_impl(context, extensions):
    assert context.profile_key != "", "PROFILE KEY NOT FOUND: %s" % str(context.profile_key)
    url = (SONAR_URL + "/api/settings/set")
    payload = {'key': 'sonar.cxx.suffixes.sources', 'value': extensions}
    _restApiSet(url, payload)


@given(u'declared header extensions of language c++ are "{extensions}"')
def step_impl(context, extensions):
    assert context.profile_key != "", "PROFILE KEY NOT FOUND: %s" % str(context.profile_key)
    url = (SONAR_URL + "/api/settings/set")
    payload = {'key': 'sonar.cxx.suffixes.headers', 'value': extensions}
    _restApiSet(url, payload)


@given(u'rule "{rule}" is enabled')
def step_impl(context, rule):
    assert context.profile_key != "", "PROFILE KEY NOT FOUND: %s" % str(context.profile_key)
    url = (SONAR_URL + "/api/qualityprofiles/activate_rule")
    payload = {'profile_key': context.profile_key, 'rule_key': rule, "severity": "MAJOR"}
    _restApiSet(url, payload)


@given(u'rule "{rule}" is created based on "{templaterule}" in repository "{repository}"')
def step_impl(context, rule, templaterule, repository):
    assert context.profile_key != "", "PROFILE KEY NOT FOUND: %s" % str(context.profile_key)
    url = (SONAR_URL + "/api/rules/create")
    payload = {'custom_key': rule, 'html_description': "nodesc", "name": rule, "severity": "MAJOR", "template_key": templaterule, "markdown_description": "nodesc"}
    _restApiSet(url, payload)
    url = (SONAR_URL + "/api/qualityprofiles/activate_rule")
    payload = {'profile_key': context.profile_key, 'rule_key': repository + ":" + rule, "severity": "MAJOR"}
    _restApiSet(url, payload)


@when(u'I run "{command}"')
def step_impl(context, command):
    _runCommand(context, command)


@then(u'the analysis finishes successfully')
def step_impl(context):
    assert context.rc == 0, "Exit code is %i, but should be zero" % context.rc


@then(u'the analysis in server has completed')
def step_impl(context):
    assert ensureComputeEngineHasFinishedOk(context.log) == "", ("Analysis in Background Task Failed")


@then(u'the analysis log contains no error/warning messages except those matching')
def step_impl(context):
    ignore_re = build_regexp(context.text)
    badlines, _errors, _warnings = analyselog(context.log, ignore_re)

    assert len(badlines) == 0,\
        ("Found following errors and/or warnings lines in the logfile:\n"
         + "".join(badlines)
         + "For details see %s" % context.log)


@then(u'delete created rule {rule}')
def step_impl(context, rule):
    url = (SONAR_URL + "/api/rules/delete")
    payload = {'key': rule}
    _restApiSet(url, payload)


@then(u'the analysis log contains no error/warning messages')
def step_impl(context):
    badlines, _errors, _warnings = analyselog(context.log)

    assert len(badlines) == 0,\
        ("Found following errors and/or warnings lines in the logfile:\n"
         + "".join(badlines)
         + "For details see %s" % context.log)


@then(u'the server log (if locatable) contains no error/warning messages')
def step_impl(context):
    if context.serverlogfd is not None:
        lines = context.serverlogfd.readlines()
        badlines, _errors, _warnings = analyseloglines(lines)

        assert len(badlines) == 0,\
            ("Found following errors and/or warnings lines in the logfile:\n"
             + "".join(badlines)
             + "For details see %s" % context.serverlog)


@then(u'the number of violations fed is {number}')
def step_impl(context, number):
    exp_measures = {"violations": float(number)}
    _assertMeasures(context.project, exp_measures)


@then(u'the following metrics have following values')
def step_impl(context):
    exp_measures = _expMeasuresToDict(context.table)
    _assertMeasures(context.project, exp_measures)


@then(u'the test related metrics have following values: {values}')
def step_impl(context, values):
    parsed_values = [value.strip() for value in values.split(",")]
    exp_measures = _expMeasuresToDict(parsed_values)
    _assertMeasures(context.project, exp_measures)


@then(u'the analysis breaks')
def step_impl(context):
    assert context.rc != 0, "Exit code is %i, but should be non zero" % context.rc


@then(u'the analysis log contains a line matching')
def step_impl(context):
    assert _containsLineMatching(context.log, context.text)


@given(u'a report outside the projects directory, e.g. "/tmp/cppcheck-v1.xml"')
def step_impl(context):
    report_fname = "cppcheck-v1.xml"
    source = os.path.join(TESTDATADIR, "cppcheck_project", report_fname)
    target = os.path.join("/tmp", report_fname)
    shutil.copyfile(source, target)


@when(u'I run sonar-scanner with following options')
def step_impl(context):
    arguments = [line for line in context.text.split("\n") if line != '']
    command = "sonar-scanner " + " ".join(arguments)
    _runCommand(context, command)





def _restApiGet(url):
    try:
        response = None
        response = requests.get(url, timeout=60, auth=HTTPBasicAuth('admin', 'admin'))
        response.raise_for_status()
        if not response.text:
            assert False, "error _restApiGet: no response %s" % url
        return response
    except requests.exceptions.RequestException as e:
        if response and response.text:
            assert False, "error _restApiGet: %s -> %s, %s" % (url, str(e), response.text)
        else:
            assert False, "error _restApiGet: %s -> %s" % (url, str(e))

def _restApiSet(url, payload):
    try:
        response = None
        response = requests.post(url, payload, timeout=60, auth=HTTPBasicAuth('admin', 'admin'))
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        if response and response.text:
            assert False, "error _restApiSet: %s -> %s, %s" % (url, str(e), response.text)
        else:
            assert False, "error _restApiSet: %s -> %s" % (url, str(e))

def _getJson(response):
    try:
        return response.json()
    except ValueError as e:
        assert False, "error _getJson: %s, %s" % (str(e), response.text)

def _expMeasuresToDict(measures):
    def convertvalue(value):
        return None if value == "None" else float(value)
    res = {}
    if isinstance(measures, model.Table):
        res = {row["metric"]: convertvalue(row["value"]) for row in measures}
    elif isinstance(measures, list):
        assert len(measures) == len(TEST_METRICS_ORDER)
        res = {}
        for i in range(len(measures) - 1):
            res[TEST_METRICS_ORDER[i]] = convertvalue(measures[i])
    return res

def _gotKeyFromQualityProfile(measures):
    return {measure["key"]: measure["name"] + " - " + measure["language"] for measure in measures}

def _gotMeasuresToDict(measures):
    return {measure["metric"]: measure["value"] for measure in measures}

def _diffMeasures(expected, measured):
    difflist = []
    for metric, value_expected in expected.iteritems():
        value_measured = measured.get(metric, None)
        append = False
        try:
            if float(value_expected) != float(value_measured):
                append = True
        except:
            if value_expected != value_measured:
                append = True
        if append:
            difflist.append("\t%s is actually %s [expected: %s]" % (metric, str(value_measured), str(value_expected)))

    return "\n".join(difflist)

def _containsLineMatching(filepath, pattern):
    pat = re.compile(pattern)
    with open(filepath) as logfo:
        for line in logfo:
            if pat.match(line):
                return True
    return False

def _assertMeasures(project, measures):
    metrics_to_query = measures.keys()
    url = (SONAR_URL + "/api/measures/component?componentKey=" + project + "&metricKeys="
           + ",".join(metrics_to_query))

    print(BRIGHT + "\nGet measures with query : " + url + RESET_ALL)
    response = _restApiGet(url)

    got_measures = {}
    json_measures = _getJson(response)["component"]["measures"]
    got_measures = _gotMeasuresToDict(json_measures)

    diff = _diffMeasures(measures, got_measures)
    assert diff == "", "\n" + diff

def _runCommand(context, command):
    context.log = "_%s_.log" % context.project

    sonarhome = os.environ.get("SONARHOME", None)
    if sonarhome:
        context.serverlog = sonarlog(sonarhome)
        if getattr(context, "serverlogfd", None) is not None:
            context.serverlogfd.close()
        context.serverlogfd = open(context.serverlog, "r")
        context.serverlogfd.seek(0, 2)
    else:
        context.serverlogfd = None

    projecthome = os.path.join(TESTDATADIR, context.project)

    with open(context.log, "w") as logfile:
        proc = subprocess.Popen(command,
                                shell=True,
                                cwd=projecthome,
                                stdout=logfile,
                                stderr=subprocess.STDOUT
                               )
        proc.communicate()

    context.rc = proc.returncode

