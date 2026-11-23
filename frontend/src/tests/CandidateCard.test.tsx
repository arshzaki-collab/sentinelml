import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CandidateCard } from "../components/scouting/CandidateCard";
import { CandidateClientView } from "../types/game";

describe("CandidateCard Component — Zero Identity Leakage & 3 Hints", () => {
  const mockCandidateST: CandidateClientView = {
    candidate_token: "cand-token-uuid-1234",
    cost_usd: 45000000,
    position: "ST",
    hints: [
      { label: "Goals (Compulsory)", value: 28, icon_key: "goals" },
      { label: "Assists", value: 9, icon_key: "assists" },
      { label: "Domestic League", value: "Premier League", icon_key: "league" },
    ],
  };

  it("renders candidate card with exactly 3 statistical hints", () => {
    const onSelect = vi.fn();
    render(
      <CandidateCard
        candidate={mockCandidateST}
        index={0}
        availableCash={1000000000}
        onSelect={onSelect}
        disabled={false}
      />
    );

    expect(screen.getByText(/Anonymous ST/i)).toBeInTheDocument();
    expect(screen.getByText(/\$45,000,000/i)).toBeInTheDocument();

    // Verify exactly 3 hints rendered
    expect(screen.getByText("Goals (Compulsory)")).toBeInTheDocument();
    expect(screen.getByText("28")).toBeInTheDocument();
    expect(screen.getByText("Assists")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getByText("Domestic League")).toBeInTheDocument();
    expect(screen.getByText("Premier League")).toBeInTheDocument();
  });

  it("never exposes secret player names or database IDs in rendered output", () => {
    const { container } = render(
      <CandidateCard
        candidate={mockCandidateST}
        index={0}
        availableCash={1000000000}
        onSelect={vi.fn()}
        disabled={false}
      />
    );

    const html = container.innerHTML;
    expect(html).not.toContain("Messi");
    expect(html).not.toContain("Ronaldo");
    expect(html).not.toContain("Haaland");
    expect(html).not.toContain("secret_player_id");
    expect(html).not.toContain("player_id");
  });

  it("disables purchase button when available cash is less than candidate cost", () => {
    const onSelect = vi.fn();
    render(
      <CandidateCard
        candidate={mockCandidateST}
        index={0}
        availableCash={30000000} // $30M < $45M cost
        onSelect={onSelect}
        disabled={false}
      />
    );

    expect(screen.getByText(/INSUFFICIENT FUNDS/i)).toBeInTheDocument();
    expect(screen.queryByText(/SIGN CANDIDATE/i)).not.toBeInTheDocument();
  });

  it("requires confirmation click before executing purchase", () => {
    const onSelect = vi.fn();
    render(
      <CandidateCard
        candidate={mockCandidateST}
        index={0}
        availableCash={1000000000}
        onSelect={onSelect}
        disabled={false}
      />
    );

    const button = screen.getByText(/SIGN CANDIDATE #1/i);
    fireEvent.click(button);

    // Prompt for confirmation
    expect(screen.getByText(/CONFIRM SIGNING\?/i)).toBeInTheDocument();
    expect(onSelect).not.toHaveBeenCalled();

    // Second click executes
    fireEvent.click(screen.getByText(/CONFIRM SIGNING\?/i));
    expect(onSelect).toHaveBeenCalledWith("cand-token-uuid-1234");
  });
});
