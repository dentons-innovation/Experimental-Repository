import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  ErrorMessage,
  LoadingSpinner,
  EmptyState,
  TaskPriorityBadge,
} from "@/components/ui";

describe("UI Components & Accessibility", () => {
  it("renders ErrorMessage with alert role", () => {
    render(<ErrorMessage message="Something went wrong" />);
    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent("Something went wrong");
  });

  it("renders LoadingSpinner with status role", () => {
    render(<LoadingSpinner />);
    const status = screen.getByRole("status");
    expect(status).toBeInTheDocument();
  });

  it("renders EmptyState with title and action button", () => {
    render(
      <EmptyState
        title="No items found"
        description="Get started by creating your first item."
        action={<button type="button">Create Item</button>}
      />,
    );
    expect(screen.getByText("No items found")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Create Item" }),
    ).toBeInTheDocument();
  });

  it("renders TaskPriorityBadge with correct labels", () => {
    const { rerender } = render(<TaskPriorityBadge priority="high" />);
    expect(screen.getByText(/high/i)).toBeInTheDocument();

    rerender(<TaskPriorityBadge priority="critical" />);
    expect(screen.getByText(/critical/i)).toBeInTheDocument();
  });
});
