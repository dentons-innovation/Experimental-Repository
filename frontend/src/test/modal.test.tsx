import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Modal } from "@/components/Modal";
import { ErrorMessage, FormField, Input, Textarea } from "@/components/ui";

function TestModalWrapper({
  initialOpen = true,
  title = "Edit Project",
  description = "Update project details and descriptions.",
  initialName = "Sample Project",
  initialDesc = "Initial description",
  onSave,
  errorMessage,
}: {
  initialOpen?: boolean;
  title?: string;
  description?: string;
  initialName?: string;
  initialDesc?: string;
  onSave?: (data: { name: string; description: string | null }) => void;
  errorMessage?: string;
}) {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const [name, setName] = useState(initialName);
  const [desc, setDesc] = useState(initialDesc);

  return (
    <div>
      <button
        type="button"
        id="open-modal-trigger"
        onClick={() => setIsOpen(true)}
      >
        Open Modal
      </button>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title={title}
        description={description}
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="test-edit-form"
              className="btn btn-primary"
            >
              Save Changes
            </button>
          </>
        }
      >
        {errorMessage && <ErrorMessage message={errorMessage} />}
        <form
          id="test-edit-form"
          onSubmit={(e) => {
            e.preventDefault();
            onSave?.({
              name: name.trim(),
              description: desc.trim() || null,
            });
          }}
        >
          <FormField label="Project Name" htmlFor="testNameInput" required>
            <Input
              id="testNameInput"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoFocus
            />
          </FormField>
          <FormField label="Description" htmlFor="testDescInput">
            <Textarea
              id="testDescInput"
              rows={3}
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
          </FormField>
        </form>
      </Modal>
    </div>
  );
}

describe("Modal Component & Dashboard Flows", () => {
  it("renders with dialog role, aria-modal, and programmatically associated labels", () => {
    render(<TestModalWrapper />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-modal", "true");

    const titleEl = screen.getByRole("heading", { name: /edit project/i });
    expect(titleEl).toBeInTheDocument();
    const titleId = titleEl.getAttribute("id");
    expect(titleId).toBeTruthy();
    expect(dialog).toHaveAttribute("aria-labelledby", titleId!);

    const descEl = screen.getByText(
      /update project details and descriptions\./i,
    );
    const descId = descEl.getAttribute("id");
    expect(descId).toBeTruthy();
    expect(dialog).toHaveAttribute("aria-describedby", descId!);
  });

  it("manages focus properly and restores focus to trigger button upon close", async () => {
    const user = userEvent.setup();
    render(<TestModalWrapper initialOpen={false} />);

    const openButton = screen.getByRole("button", { name: /open modal/i });
    openButton.focus();
    expect(document.activeElement).toBe(openButton);

    await user.click(openButton);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();

    // Input with autoFocus should be focused
    await waitFor(() => {
      const nameInput = screen.getByLabelText(/project name/i);
      expect(document.activeElement).toBe(nameInput);
    });

    // Close on Escape key
    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    // Focus should be restored to the trigger button
    await waitFor(() => {
      expect(document.activeElement).toBe(openButton);
    });
  });

  it("sends null for cleared descriptions when saved", async () => {
    const user = userEvent.setup();
    const handleSave = vi.fn();

    render(
      <TestModalWrapper
        initialName="Alpha Project"
        initialDesc="Old description"
        onSave={handleSave}
      />,
    );

    const descInput = screen.getByLabelText(/description/i);
    expect(descInput).toHaveValue("Old description");

    await user.clear(descInput);
    expect(descInput).toHaveValue("");

    const saveButton = screen.getByRole("button", { name: /save changes/i });
    await user.click(saveButton);

    expect(handleSave).toHaveBeenCalledWith({
      name: "Alpha Project",
      description: null,
    });
  });

  it("displays accessible visible error messages when mutation fails", () => {
    render(
      <TestModalWrapper errorMessage="A project with slug 'sample-project' already exists" />,
    );

    const errorAlert = screen.getByRole("alert");
    expect(errorAlert).toBeInTheDocument();
    expect(errorAlert).toHaveTextContent(/already exists/i);
  });
});
