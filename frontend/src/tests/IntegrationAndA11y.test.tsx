import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from '../App';
import { GameProvider } from '../context/GameContext';
import { Header } from '../components/common/Header';
import { InstructionsModal } from '../components/menu/InstructionsModal';
import { soundManager } from '../services/sound';

describe('Frontend Integration & Accessibility Audit', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders application with accessible landmark headings and interactive buttons', () => {
    render(
      <GameProvider>
        <App />
      </GameProvider>
    );

    // Main branding and headings
    expect(screen.getAllByText(/blind billion/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/2\.0/i).length).toBeGreaterThanOrEqual(1);

    // Mode buttons with accessible labels
    const spBtn = screen.getByRole('button', { name: /single player \(vs ai\)/i });
    const mpBtn = screen.getByRole('button', { name: /multiplayer \(online\)/i });
    const rulesBtn = screen.getByRole('button', { name: /how to play/i });

    expect(spBtn).toBeEnabled();
    expect(mpBtn).toBeEnabled();
    expect(rulesBtn).toBeEnabled();
  });

  it('InstructionsModal implements accessible dialog attributes and can be dismissed', () => {
    const handleClose = vi.fn();
    render(<InstructionsModal isOpen={true} onClose={handleClose} />);

    // Verify dialog role and title
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(screen.getByText('HOW TO PLAY BLIND BILLION 2.0')).toBeInTheDocument();

    // Verify all 5 rule sections are readable
    expect(screen.getByText(/Starting Capital/i)).toBeInTheDocument();
    expect(screen.getByText(/7 Required Squad Slots/i)).toBeInTheDocument();
    expect(screen.getByText(/Blind Scouting & 3 Compulsory Hints/i)).toBeInTheDocument();
    expect(screen.getByText(/Transfer Windows \(2019, 2022, 2025\)/i)).toBeInTheDocument();
    expect(screen.getByText(/2026 Settlement & Final Victory/i)).toBeInTheDocument();

    // Close button triggers callback
    const closeBtn = screen.getByRole('button', { name: /got it/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('Header displays sound toggle with persistent state and accessible labels', () => {
    render(
      <GameProvider>
        <Header />
      </GameProvider>
    );

    // Sound toggle button by aria-label
    const soundToggle = screen.getByRole('button', { name: /mute audio|unmute audio/i });
    expect(soundToggle).toBeInTheDocument();

    // Initial state is unmuted (sound enabled)
    expect(soundManager.getMuted()).toBe(false);

    // Click to mute
    fireEvent.click(soundToggle);
    expect(soundManager.getMuted()).toBe(true);

    // Click again to unmute
    fireEvent.click(soundToggle);
    expect(soundManager.getMuted()).toBe(false);
  });

  it('navigates from Main Menu to Single-Player Setup and back', () => {
    render(
      <GameProvider>
        <App />
      </GameProvider>
    );

    // Click Single Player
    const spBtn = screen.getByRole('button', { name: /single player \(vs ai\)/i });
    fireEvent.click(spBtn);

    // Verify setup screen is rendered with AI difficulty options
    expect(screen.getByText('SINGLE PLAYER (VS AI)')).toBeInTheDocument();
    expect(screen.getByText('AI DIFFICULTY')).toBeInTheDocument();
    expect(screen.getByText('ROOKIE')).toBeInTheDocument();
    expect(screen.getByText('PRO')).toBeInTheDocument();
    expect(screen.getByText('LEGEND')).toBeInTheDocument();

    // Click Back to return to Main Menu
    const backBtn = screen.getByRole('button', { name: /back to menu/i });
    fireEvent.click(backBtn);

    // Back on Main Menu
    expect(screen.getAllByText(/blind billion/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('button', { name: /single player \(vs ai\)/i })).toBeInTheDocument();
  });
});
