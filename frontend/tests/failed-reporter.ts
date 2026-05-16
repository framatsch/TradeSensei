/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { Reporter, TestCase, TestResult } from '@playwright/test/reporter';
import * as fs from 'fs';

class FailedReporter implements Reporter {
  private failedTests: string[] = [];

  onTestEnd(test: TestCase, result: TestResult) {
    if (result.status === 'failed' || result.status === 'timedOut') {
      this.failedTests.push(`${test.title} (${test.location.file})`);
    }
  }

  onEnd() {
    if (this.failedTests.length > 0) {
      fs.writeFileSync('failed_tests.txt', this.failedTests.join('\n'));
    }
  }
}
export default FailedReporter;
