/**
 * Tests for ConnectSchwabButton component.
 *
 * Navigation is tested by passing a mock `navigate` prop — this avoids
 * fighting jsdom's non-configurable window.location property.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConnectSchwabButton } from "@/components/broker/ConnectSchwabButton";

describe("ConnectSchwabButton", () => {
  it("renders a button with 'Connect Schwab' text", () => {
    render(<ConnectSchwabButton />);
    expect(screen.getByRole("button", { name: /connect schwab/i })).toBeInTheDocument();
  });

  it("has correct data-testid", () => {
    render(<ConnectSchwabButton />);
    expect(screen.getByTestId("connect-schwab-button")).toBeInTheDocument();
  });

  it("navigates to the backend connect endpoint on click", () => {
    const mockNavigate = jest.fn();
    render(<ConnectSchwabButton navigate={mockNavigate} />);
    fireEvent.click(screen.getByTestId("connect-schwab-button"));
    expect(mockNavigate).toHaveBeenCalledWith("/api/v1/broker/schwab/connect");
  });

  it("applies additional className prop", () => {
    render(<ConnectSchwabButton className="extra-class" />);
    const btn = screen.getByTestId("connect-schwab-button");
    expect(btn.className).toContain("extra-class");
  });

  it("displays the Schwab 'S' icon", () => {
    render(<ConnectSchwabButton />);
    expect(screen.getByText("S")).toBeInTheDocument();
  });
});
