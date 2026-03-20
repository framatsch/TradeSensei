# Skill: Technical Debt & Code Bloat Elimination
**Description:** Specialized skill for identifying and removing redundant code, dead logic, and inconsistent implementation patterns in Python (Backend) and TypeScript (Frontend) environments.

**Operational Procedures:**
1. **DRY Principle Audit (Don't Repeat Yourself):** - Scan backend controllers and frontend hooks for near-identical logic blocks.
   - Look for duplicated financial math (e.g., CAGR, Drawdown, Sharpe Ratio) or API error handling.
   - Propose centralized utility functions or decorators.

2. **Dead Code & Unused Assets:** - Identify functions, variables, and components that are defined but never imported or invoked.
   - Locate orphaned CSS classes and unused TypeScript interfaces.

3. **Complexity & Abstraction Review:** - Detect deeply nested if-else structures in trading logic.
   - Suggest flattening via Guard Clauses or the Strategy Pattern.
   - Flag "God Objects" (files exceeding 500 lines) for modularization.

4. **Dependency & Boilerplate Reduction:** - Check for overlapping libraries (e.g., multiple charting helpers or date parsers).
   - Identify AI-generated boilerplate that can be replaced by native language features.

**Output Requirements:**
- Generate a "Refactoring Candidates" report.
- Each candidate must include: File path, line range, rationale for the bloat, and estimated LOC (Lines of Code) reduction.
- Provide a "Safe to Delete" vs. "Requires Review" classification.

**Git Workflow Instructions:**
1. **Branch Creation:** Before applying any changes, create a new branch named `refactor/bloat-reduction-[timestamp]`.
2. **Atomic Commits:** Group related refactorings into small, descriptive commits (e.g., "refactor: consolidate trading math utils").
3. **Validation:** After refactoring, run the existing test suite (if available) to ensure zero regression.
4. **Summary:** Provide a final report including the branch name and a diff summary of removed lines.