// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { v2Api, type MemoryRes } from "@/lib/api/v2";
import MemoriesPage from "./MemoriesPage";

vi.mock("@/lib/api/v2", () => ({
  v2Api: {
    memories: {
      list: vi.fn(),
      archive: vi.fn(),
    },
    // Used by Layout's TeamSelector.
    teams: { list: vi.fn(async () => []) },
  },
}));

const listMock = vi.mocked(v2Api.memories.list);
const archiveMock = vi.mocked(v2Api.memories.archive);

const ARCHIVE_BUTTON_NAME = /Archive/;

function makeMemory(overrides: Partial<MemoryRes> = {}): MemoryRes {
  return {
    id: "mem-1",
    kind: "fact",
    content: "User prefers pnpm over npm",
    salience: 7.5,
    evidence: null,
    project_id: null,
    source_session_id: null,
    archived: false,
    created_at: "2026-09-01T10:00:00",
    updated_at: "2026-09-05T12:30:00",
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/settings/memories"]}>
      <MemoriesPage />
    </MemoryRouter>,
  );
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  listMock.mockReset();
  archiveMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("MemoriesPage", () => {
  it("renders the memory list with kind badges and metadata", async () => {
    listMock.mockResolvedValue([
      makeMemory(),
      makeMemory({
        id: "mem-2",
        kind: "gotcha",
        content: "Never run tests without isolated share dir",
        salience: 9,
        evidence: "tests/web broke on 2026-09-03",
      }),
    ]);

    renderPage();

    expect(await screen.findByText("User prefers pnpm over npm")).toBeTruthy();
    expect(
      screen.getByText("Never run tests without isolated share dir"),
    ).toBeTruthy();
    expect(screen.getByText("Fact")).toBeTruthy();
    expect(screen.getByText("Gotcha")).toBeTruthy();
    expect(screen.getByText("Salience 7.5")).toBeTruthy();
    expect(screen.getByText("Salience 9.0")).toBeTruthy();
    // Evidence stays collapsed until toggled.
    expect(
      screen.queryByText("tests/web broke on 2026-09-03"),
    ).toBeNull();
    expect(listMock).toHaveBeenCalledWith({
      q: undefined,
      includeArchived: false,
      limit: 50,
      offset: 0,
    });
  });

  it("archives a memory after confirmation and removes it from the list", async () => {
    window.confirm = vi.fn(() => true);
    listMock.mockResolvedValue([makeMemory()]);
    archiveMock.mockResolvedValue({ detail: "Memory archived" });

    renderPage();
    expect(await screen.findByText("User prefers pnpm over npm")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: ARCHIVE_BUTTON_NAME }));

    await waitFor(() => {
      expect(archiveMock).toHaveBeenCalledWith("mem-1");
    });
    await waitFor(() => {
      expect(screen.queryByText("User prefers pnpm over npm")).toBeNull();
    });
    expect(await screen.findByText("Memory archived")).toBeTruthy();
  });

  it("keeps the memory when the archive confirmation is cancelled", async () => {
    window.confirm = vi.fn(() => false);
    listMock.mockResolvedValue([makeMemory()]);

    renderPage();
    expect(await screen.findByText("User prefers pnpm over npm")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: ARCHIVE_BUTTON_NAME }));

    expect(archiveMock).not.toHaveBeenCalled();
    expect(screen.getByText("User prefers pnpm over npm")).toBeTruthy();
  });

  it("shows the empty state when there are no memories", async () => {
    listMock.mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText("No memories yet")).toBeTruthy();
  });

  it("prompts to log in again when the API rejects with 401", async () => {
    listMock.mockRejectedValue(new Error("Invalid authentication credentials"));

    renderPage();

    expect(
      await screen.findByText("Session expired, please log in again"),
    ).toBeTruthy();
  });
});
