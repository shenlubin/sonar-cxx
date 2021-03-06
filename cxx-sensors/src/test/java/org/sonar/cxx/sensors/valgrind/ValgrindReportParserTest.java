/*
 * Sonar C++ Plugin (Community)
 * Copyright (C) 2010-2017 SonarOpenCommunity
 * http://github.com/SonarOpenCommunity/sonar-cxx
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.cxx.sensors.valgrind;

import org.sonar.cxx.sensors.valgrind.ValgrindReportParser;
import org.sonar.cxx.sensors.valgrind.ValgrindError;
import static org.junit.Assert.assertEquals;

import java.io.File;
import java.util.Set;

import org.junit.Before;
import org.junit.Test;
import org.sonar.cxx.sensors.utils.TestUtils;

public class ValgrindReportParserTest {

  private ValgrindReportParser parser;
  @Before
  public void setUp() {
    parser = new ValgrindReportParser();
    TestUtils.mockFileSystem();
  }

  @Test
  public void shouldParseCorrectNumberOfErrors() throws javax.xml.stream.XMLStreamException {
    File absReportsProject = TestUtils.loadResource("/org/sonar/cxx/sensors/reports-project").getAbsoluteFile();
    File absReportFile = new File(absReportsProject, "valgrind-reports/valgrind-result-SAMPLE.xml");    
    Set<ValgrindError> valgrindErrors = parser.processReport(absReportFile);
    assertEquals(valgrindErrors.size(), 6);
  }

  @Test(expected = javax.xml.stream.XMLStreamException.class)
  public void shouldThrowWhenGivenAnIncompleteReport_1() throws javax.xml.stream.XMLStreamException {
    File absReportsProject = TestUtils.loadResource("/org/sonar/cxx/sensors/reports-project").getAbsoluteFile();
    File absReportFile = new File(absReportsProject, "valgrind-reports/incorrect-valgrind-result_1.xml");
    
    // error contains no kind-tag    
    parser.processReport(absReportFile);
  }

  @Test(expected = javax.xml.stream.XMLStreamException.class)
  public void shouldThrowWhenGivenAnIncompleteReport_2() throws javax.xml.stream.XMLStreamException {
    File absReportsProject = TestUtils.loadResource("/org/sonar/cxx/sensors/reports-project").getAbsoluteFile();
    File absReportFile = new File(absReportsProject, "valgrind-reports/incorrect-valgrind-result_2.xml");
    
    // error contains no what- or xwhat-tag
    parser.processReport(absReportFile);
  }

  @Test(expected = javax.xml.stream.XMLStreamException.class)
  public void shouldThrowWhenGivenAnIncompleteReport_3() throws javax.xml.stream.XMLStreamException {
    File absReportsProject = TestUtils.loadResource("/org/sonar/cxx/sensors/reports-project").getAbsoluteFile();
    File absReportFile = new File(absReportsProject, "valgrind-reports/incorrect-valgrind-result_3.xml");    
    // error contains no stack-tag
    parser.processReport(absReportFile);
  }
}
