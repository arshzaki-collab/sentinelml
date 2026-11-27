import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StadiumDashboard } from '../components/dashboard/StadiumDashboard';
import { ErrorBoundary } from '../components/common/ErrorBoundary';
import { CandidateCard } from '../components/scouting/CandidateCard';
import { FormationPitch } from '../components/dashboard/FormationPitch';
import { RoomPublicView, PlayerGameStateView } from '../types/game';

// Mock framer-motion to render elements simply in Vitest JSDOM
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, ...props }: any) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
    header: ({ children, className, ...props }: any) => (
      <header className={className} {...props}>
        {children}
      </header>
    ),
    section: ({ children, className, ...props }: any) => (
      <section className={className} {...props}>
        {children}
      </section>
    ),
    button: ({ children, className, onClick, disabled, ...props }: any) => (
      <button className={className} onClick={onClick} disabled={disabled} {...props}>
        {children}
      </button>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mutable mock state for useGame hook
let mockGameState: {
  room: RoomPublicView | null;
  myState: PlayerGameStateView | null;
  playerId: string;
  sessionToken: string;
  error: string | null;
  isLoading: boolean;
  submitAction: (payload: any) => Promise<any>;
  refreshState: () => Promise<void>;
  returnToLobby: () => void;
};

vi.mock('../context/GameContext', () => ({
  useGame: () => mockGameState,
}));

describe('Game Screen Rendering & Crash Prevention Test Suite', () => {
  const mockRoom: RoomPublicView = {
    room_code: 'TEST',
    status: 'IN_GAME',
    host_player_id: 'player-1',
    current_year: 2016,
    current_phase: 'BUYING_SEASON',
    current_slot_index: 1,
    timeline_step_index: 0,
    created_at: new Date().toISOString(),
    is_game_started: true,
    is_completed: false,
    players: [
      {
        player_id: 'player-1',
        display_name: 'TacticianOne (Host)',
        is_host: true,
        is_ready: true,
        is_connected: true,
        is_turn_submitted: false,
        joined_at: new Date().toISOString(),
        is_ai: false,
        ai_difficulty: null,
      },
      {
        player_id: 'ai-rookie-1',
        display_name: 'Scout AI (Rookie)',
        is_host: false,
        is_ready: true,
        is_connected: true,
        is_turn_submitted: false,
        joined_at: new Date().toISOString(),
        is_ai: true,
        ai_difficulty: 'ROOKIE',
      },
    ],
  };

  const mockActiveGameState: PlayerGameStateView = {
    player_id: 'player-1',
    display_name: 'TacticianOne (Host)',
    cash_balance: 1000000000,
    current_year: 2016,
    current_phase: 'BUYING_SEASON',
    active_slot_index: 1,
    timeline_step_index: 0,
    filled_slots_count: 0,
    is_completed: false,
    final_net_worth: null,
    final_squad_value: null,
    transaction_history: [],
    slots: [
      {
        slot_index: 1,
        position: 'ST',
        required_position: 'ST',
        buying_year: 2016,
        is_filled: false,
        purchase_price_usd: null,
      },
      {
        slot_index: 2,
        position: 'WG',
        required_position: 'WG',
        buying_year: 2017,
        is_filled: false,
        purchase_price_usd: null,
      },
      {
        slot_index: 3,
        position: 'CM',
        required_position: 'CM',
        buying_year: 2018,
        is_filled: false,
        purchase_price_usd: null,
      },
      {
        slot_index: 4,
        position: 'CB',
        required_position: 'CB',
        buying_year: 2020,
        is_filled: false,
        purchase_price_usd: null,
      },
      {
        slot_index: 5,
        position: 'CM',
        required_position: 'CM',
        buying_year: 2021,
        is_filled: false,
        purchase_price_usd: null,
      },
      {
        slot_index: 6,
        position: 'CB',
        required_position: 'CB',
        buying_year: 2023,
        is_filled: false,
        purchase_price_usd: null,
      },
      {
        slot_index: 7,
        position: 'GK',
        required_position: 'GK',
        buying_year: 2024,
        is_filled: false,
        purchase_price_usd: null,
      },
    ],
    shortlists: {
      '1': {
        slot_index: 1,
        required_position: 'ST',
        buying_year: 2016,
        candidates: [
          {
            candidate_token: 'cand-st-1',
            cost_usd: 65000000,
            position: 'ST',
            hints: {
              'Goals (Compulsory)': 31,
              'Assists': 8,
              'Domestic League': 'La Liga',
            },
          },
          {
            candidate_token: 'cand-st-2',
            cost_usd: 48000000,
            position: 'ST',
            hints: {
              'Goals (Compulsory)': 22,
              'Assists': 11,
              'Domestic League': 'Premier League',
            },
          },
          {
            candidate_token: 'cand-st-3',
            cost_usd: 72000000,
            position: 'ST',
            hints: {
              'Goals (Compulsory)': 29,
              'Assists': 5,
              'Domestic League': 'Bundesliga',
            },
          },
          {
            candidate_token: 'cand-st-4',
            cost_usd: 35000000,
            position: 'ST',
            hints: {
              'Goals (Compulsory)': 18,
              'Assists': 14,
              'Domestic League': 'Serie A',
            },
          },
        ],
      },
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockGameState = {
      room: mockRoom,
      myState: mockActiveGameState,
      playerId: 'player-1',
      sessionToken: 'test-session-token',
      error: null,
      isLoading: false,
      submitAction: vi.fn(),
      refreshState: vi.fn(),
      returnToLobby: vi.fn(),
    };
  });

  it('renders StadiumDashboard with all subcomponents and 4 anonymous candidates', () => {
    render(<StadiumDashboard />);

    // Verify timeline year and phase
    expect(screen.getAllByText('2016').length).toBeGreaterThanOrEqual(1);

    // Verify financial metrics
    expect(screen.getAllByText(/\$1,000,000,000/i).length).toBeGreaterThanOrEqual(1);

    // Verify 4 anonymous candidate cards are present
    const candidateHeadings = screen.getAllByText(/Anonymous ST/i);
    expect(candidateHeadings).toHaveLength(4);

    // Verify candidate dictionary hints are rendered without throwing
    expect(screen.getByText('La Liga')).toBeInTheDocument();
    expect(screen.getByText('Premier League')).toBeInTheDocument();
    expect(screen.getByText('Bundesliga')).toBeInTheDocument();
    expect(screen.getByText('Serie A')).toBeInTheDocument();
  });

  it('renders CandidateCard with dictionary hints seamlessly without crashing', () => {
    const candidateWithDictHints = {
      candidate_token: 'dict-token-1',
      cost_usd: 50000000,
      position: 'ST',
      hints: {
        'Goals (Compulsory)': 27,
        'Assists': 12,
        'Domestic League': 'Ligue 1',
      },
    };

    render(
      <CandidateCard
        candidate={candidateWithDictHints}
        index={0}
        availableCash={1000000000}
        onSelect={vi.fn()}
        disabled={false}
      />
    );

    expect(screen.getByText(/Anonymous ST/i)).toBeInTheDocument();
    expect(screen.getByText('Goals (Compulsory)')).toBeInTheDocument();
    expect(screen.getByText('27')).toBeInTheDocument();
    expect(screen.getByText('Assists')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Domestic League')).toBeInTheDocument();
    expect(screen.getByText('Ligue 1')).toBeInTheDocument();
  });

  it('renders StadiumDashboard loading state when myState is null without showing a blank screen', () => {
    mockGameState.myState = null;

    const { container } = render(<StadiumDashboard />);

    expect(container.innerHTML).not.toBe('');
    expect(screen.getByText(/Loading Tactical Dashboard\.\.\./i)).toBeInTheDocument();
    expect(screen.getByText(/Synchronizing server-authoritative game state/i)).toBeInTheDocument();
  });

  it('renders retry button in StadiumDashboard when myState is null and error is present', () => {
    mockGameState.myState = null;
    mockGameState.error = 'Network connection reset by peer';

    render(<StadiumDashboard />);

    expect(screen.getByText('Network connection reset by peer')).toBeInTheDocument();
    const retryBtn = screen.getByRole('button', { name: /retry sync/i });
    expect(retryBtn).toBeInTheDocument();

    fireEvent.click(retryBtn);
    expect(mockGameState.refreshState).toHaveBeenCalledTimes(1);
  });

  it('renders FormationPitch with both position and required_position fallbacks', () => {
    mockGameState.myState = {
      ...mockActiveGameState,
      slots: [
        {
          slot_index: 1,
          required_position: 'ST',
          buying_year: 2016,
          is_filled: true,
          current_player_name: 'Revealed Striker',
          purchase_price_usd: 80000000,
        },
        {
          slot_index: 2,
          position: 'WG',
          buying_year: 2017,
          is_filled: false,
          purchase_price_usd: null,
        },
      ],
    };

    render(<FormationPitch />);

    // Slot 1 shows ST and filled cost
    expect(screen.getByText('ST')).toBeInTheDocument();
    expect(screen.getByText('Revealed Striker')).toBeInTheDocument();
    expect(screen.getByText('$80,000,000')).toBeInTheDocument();

    // Slot 2 shows WG and Empty Slot 2
    expect(screen.getByText('WG')).toBeInTheDocument();
    expect(screen.getByText('Empty Slot 2')).toBeInTheDocument();
  });

  it('ErrorBoundary catches unexpected child errors and presents recovery controls', () => {
    // Suppress console.error in Vitest for the intentional throw
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const BrokenChild = () => {
      throw new Error('Critical simulation engine fault');
    };

    render(
      <ErrorBoundary>
        <BrokenChild />
      </ErrorBoundary>
    );

    expect(screen.getByText('Tactical Interface Failure')).toBeInTheDocument();
    expect(
      screen.getByText(/An unexpected error occurred while rendering the game interface\./i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Critical simulation engine fault/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /main menu/i })).toBeInTheDocument();

    consoleErrorSpy.mockRestore();
  });
});
