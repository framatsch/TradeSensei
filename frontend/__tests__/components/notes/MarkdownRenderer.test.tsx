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

/**
 * Tests for MarkdownRenderer component.
 *
 * react-markdown and remark-gfm are ESM modules that cannot be transformed
 * by babel-jest, so they are mocked here via jest.mock().
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { MarkdownRenderer } from "@/components/notes/MarkdownRenderer";

// Mock ESM-only packages
jest.mock("react-markdown", () => {
  const ReactMarkdownMock = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="markdown-content">{children}</div>
  );
  ReactMarkdownMock.displayName = "ReactMarkdown";
  return ReactMarkdownMock;
});

jest.mock("remark-gfm", () => () => {});

describe("MarkdownRenderer", () => {
  it("renders plain text content", () => {
    render(<MarkdownRenderer content="Hello world" />);
    expect(screen.getByTestId("markdown-content")).toHaveTextContent(
      "Hello world"
    );
  });

  it("renders markdown-like content as a string (delegated to ReactMarkdown mock)", () => {
    render(<MarkdownRenderer content="**bold text**" />);
    expect(screen.getByTestId("markdown-content")).toHaveTextContent(
      "**bold text**"
    );
  });

  it("applies prose wrapper classes", () => {
    const { container } = render(<MarkdownRenderer content="test" />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("prose");
    expect(wrapper.className).toContain("prose-invert");
    expect(wrapper.className).toContain("prose-sm");
  });

  it("applies additional className when provided", () => {
    const { container } = render(
      <MarkdownRenderer content="test" className="extra-class" />
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("extra-class");
  });

  it("renders empty string content without crashing", () => {
    render(<MarkdownRenderer content="" />);
    expect(screen.getByTestId("markdown-content")).toBeInTheDocument();
  });

  it("renders multiline content", () => {
    const content = "Line 1\nLine 2\nLine 3";
    render(<MarkdownRenderer content={content} />);
    expect(screen.getByTestId("markdown-content")).toBeInTheDocument();
  });
});
