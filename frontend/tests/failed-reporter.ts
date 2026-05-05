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
