import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MainMenu } from "../components/menu/MainMenu";

describe("MainMenu Component", () => {
  it("renders Blind Billion 2.0 branding and core highlights", () => {
    const handleSelectMode = vi.fn();
    render(<MainMenu onSelectMode={handleSelectMode} />);

    expect(screen.getByText(/BLIND BILLION/i)).toBeInTheDocument();
    expect(screen.getByText(/\$1,000,000,000/i)).toBeInTheDocument();
    expect(screen.getByText(/SINGLE PLAYER \(VS AI\)/i)).toBeInTheDocument();
    expect(screen.getByText(/MULTIPLAYER \(ONLINE\)/i)).toBeInTheDocument();
  });

  it("triggers mode selection when Single Player or Multiplayer is clicked", () => {
    const handleSelectMode = vi.fn();
    render(<MainMenu onSelectMode={handleSelectMode} />);

    fireEvent.click(screen.getByText(/SINGLE PLAYER \(VS AI\)/i));
    expect(handleSelectMode).toHaveBeenCalledWith("single");

    fireEvent.click(screen.getByText(/MULTIPLAYER \(ONLINE\)/i));
    expect(handleSelectMode).toHaveBeenCalledWith("multiplayer");
  });

  it("opens instructions modal when rules button is clicked", () => {
    render(<MainMenu onSelectMode={vi.fn()} />);

    expect(screen.queryByText(/HOW TO PLAY BLIND BILLION 2.0/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByText(/HOW TO PLAY & TOURNAMENT RULES/i));
    expect(screen.getByText(/HOW TO PLAY BLIND BILLION 2.0/i)).toBeInTheDocument();
    expect(screen.getByText(/7 Required Squad Slots/i)).toBeInTheDocument();
  });
});
