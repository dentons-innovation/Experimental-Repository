/**
 * Workspaces list page — landing page after sign-in.
 */

import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gsap } from "gsap";
import { Plus, FolderOpen } from "lucide-react";
import { queryKeys } from "@/api/queryKeys";
import { workspacesApi } from "@/api/fetchers";
import { getApiErrorMessage } from "@/api/client";
import {
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  Modal,
  FormField,
  Input,
  Textarea,
} from "@/components/ui";
import type { Workspace } from "@/types";

export function WorkspacesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const cardsRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => workspacesApi.list({ page: 1, page_size: 50 }),
  });

  useEffect(() => {
    if (data && cardsRef.current) {
      gsap.fromTo(
        cardsRef.current.children,
        { y: 20, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.4,
          stagger: 0.06,
          ease: "power2.out",
        }
      );
    }
  }, [data]);

  if (isLoading) return <LoadingSpinner fullPage />;
  if (error) return <ErrorMessage message={getApiErrorMessage(error)} />;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Workspaces</h1>
          <p className="page-subtitle">
            {data?.total ?? 0} workspace
            {data?.total !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          id="create-workspace-btn"
          className="btn btn-primary"
          onClick={() => setShowCreate(true)}
        >
          <Plus size={16} />
          New Workspace
        </button>
      </div>

      <div className="page-content">
        {data?.items.length === 0 ? (
          <EmptyState
            title="No workspaces yet"
            description="Create your first workspace to start managing projects"
            action={
              <button
                className="btn btn-primary"
                onClick={() => setShowCreate(true)}
              >
                <Plus size={16} />
                Create Workspace
              </button>
            }
          />
        ) : (
          <div
            ref={cardsRef}
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "var(--space-4)",
            }}
          >
            {data?.items.map((ws) => (
              <WorkspaceCard
                key={ws.id}
                workspace={ws}
                onClick={() => navigate(`/workspaces/${ws.id}`)}
              />
            ))}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateWorkspaceModal
          onClose={() => setShowCreate(false)}
          onSuccess={(ws) => {
            setShowCreate(false);
            queryClient.invalidateQueries({
              queryKey: queryKeys.workspaces.all(),
            });
            navigate(`/workspaces/${ws.id}`);
          }}
        />
      )}
    </div>
  );
}

function WorkspaceCard({
  workspace,
  onClick,
}: {
  workspace: Workspace;
  onClick: () => void;
}) {
  return (
    <div
      id={`workspace-${workspace.id}`}
      className="card card-hover"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-3)",
          marginBottom: "var(--space-3)",
        }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: "var(--radius-md)",
            background: "var(--color-brand-muted)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 18,
            fontWeight: 700,
            color: "var(--color-brand)",
          }}
        >
          {workspace.name[0]?.toUpperCase()}
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{workspace.name}</div>
          <div className="text-secondary text-sm">/{workspace.slug}</div>
        </div>
      </div>
      {workspace.description && (
        <p
          style={{
            fontSize: 13,
            color: "var(--color-text-secondary)",
            lineHeight: 1.5,
          }}
        >
          {workspace.description}
        </p>
      )}
      <div
        className="divider"
        style={{ margin: "var(--space-3) 0 var(--space-2)" }}
      />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <FolderOpen size={13} color="var(--color-text-tertiary)" />
          <span className="text-secondary text-sm">Projects</span>
        </div>
        <span className="text-secondary text-sm">
          {new Date(workspace.created_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}

function CreateWorkspaceModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (ws: Workspace) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: workspacesApi.create,
    onSuccess: onSuccess,
    onError: (err) => setError(getApiErrorMessage(err)),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    mutation.mutate({ name: name.trim(), description: description.trim() || undefined });
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Create Workspace"
      description="Workspaces group projects, members, and organization settings."
      footer={
        <>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="submit"
            form="create-workspace-form"
            className="btn btn-primary"
            disabled={mutation.isPending || !name.trim()}
            id="create-workspace-submit"
          >
            {mutation.isPending ? "Creating…" : "Create Workspace"}
          </button>
        </>
      }
    >
      <form id="create-workspace-form" onSubmit={handleSubmit}>
        {error && (
          <div className="error-state" style={{ marginBottom: "var(--space-4)" }}>
            {error}
          </div>
        )}
        <FormField label="Name" htmlFor="ws-name" required>
          <Input
            id="ws-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Engineering, Marketing"
            autoFocus
            required
          />
        </FormField>
        <FormField
          label="Description"
          htmlFor="ws-description"
          helperText="What will this workspace be used for?"
        >
          <Textarea
            id="ws-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Core engineering tasks and architecture planning"
          />
        </FormField>
      </form>
    </Modal>
  );
}
