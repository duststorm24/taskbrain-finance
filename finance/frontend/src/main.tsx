import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { usePlaidLink } from "react-plaid-link";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./styles.css";

declare global {
  interface Window {
    taskbrainFinanceRoot?: ReturnType<typeof createRoot>;
  }
}

type HealthResponse = {
  ok: boolean;
  secure_config_present: boolean;
  openai_key_configured: boolean;
  plaid_configured: boolean;
};

type UserResponse = {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
};

type SessionResponse = {
  user: UserResponse;
};

type PlaidItem = {
  item_id: string;
  status: string;
  created_at?: string | null;
  last_successful_sync_at?: string | null;
};

type FinanceAccount = {
  id: string;
  name: string;
  type: string;
  subtype?: string | null;
  classification: string;
  currentBalanceCents: number;
  availableBalanceCents?: number | null;
  lastBalanceAt?: string | null;
};

type NetWorthResponse = {
  currentNetWorthCents: number;
  assetsCents: number;
  debtsCents: number;
  trend: Array<{ date: string; netWorthCents: number }>;
  accounts: FinanceAccount[];
};

type PlannedExpense = {
  id: string;
  title: string;
  due_date: string;
  amount_cents: number;
  category?: string | null;
  notes?: string | null;
};

type CashFlowMonth = {
  month: string;
  incomeCents: number;
  expenseCents: number;
  netCents: number;
  transactionCount: number;
};

type CategorySpend = {
  category: string;
  spentCents: number;
  transactionCount: number;
};

type RecentTransaction = {
  id: string;
  postedDate: string;
  description: string;
  cashFlowCents: number;
  category: string;
  pending: boolean;
};

type CashFlowResponse = {
  incomeCents: number;
  expenseCents: number;
  netCents: number;
  monthlyCashFlow: CashFlowMonth[];
  categories: CategorySpend[];
  recentTransactions: RecentTransaction[];
};

type RecurringStream = {
  id: string;
  direction: "inflow" | "outflow";
  merchantName?: string | null;
  description: string;
  frequency?: string | null;
  averageAmountCents: number;
  lastAmountCents?: number | null;
  firstDate?: string | null;
  lastDate?: string | null;
  nextExpectedDate?: string | null;
};

type CashFlowChartPoint = {
  date: string;
  income: number;
  expense?: number;
  routineOutflow?: number;
  oneTime?: number;
  net: number;
  endingCash?: number;
  transactionCount: number;
};

type Timeline = "month" | "quarter" | "year" | "all";

const API_BASE = "/api/finance";
const timelineMonths: Record<Timeline, number> = {
  month: 1,
  quarter: 3,
  year: 12,
  all: 36,
};

const privacyPolicySections = [
  {
    title: "What TaskBrain Finance is",
    body:
      "TaskBrain Finance is a self-hosted personal finance dashboard used to organize account balances, transactions, recurring expenses, investments, debts, planned expenses, cash flow, and net worth. It is intended to run locally on a private machine and is not designed for public internet exposure.",
  },
  {
    title: "Data collected with your consent",
    body:
      "When you connect an institution through Plaid Link, the app may receive account metadata, balances, transactions, recurring transaction streams, investment holdings and investment transactions, and liability details such as loans or credit card balances. The app may also store planning inputs you enter directly, such as future one-time expenses, budget categories, notes, and forecast assumptions.",
  },
  {
    title: "How the data is used",
    body:
      "Financial data is used to show dashboards, charts, budget tracking, cash flow forecasts, debt and investment views, recurring expense summaries, and personal financial recommendations. The app does not initiate payments, transfers, account changes, or trades.",
  },
  {
    title: "Storage and security",
    body:
      "Data is stored locally in SQLite on the machine running the application. Plaid access tokens and other sensitive integration tokens are encrypted before storage using an application encryption key. API keys and application secrets are loaded from environment variables and are not committed to the public code repository.",
  },
  {
    title: "Sharing and AI analysis",
    body:
      "TaskBrain Finance does not sell consumer financial data. Plaid is used to retrieve financial data after consent through Plaid Link. OpenAI may be used to generate summaries or recommendations from selected financial context; prompts should avoid unnecessary sensitive identifiers where possible.",
  },
  {
    title: "Retention and deletion",
    body:
      "Data remains on the local system until it is deleted by the owner/operator. Because this is a self-hosted application, deleting local database files or disconnecting Plaid Items removes local access to stored financial data. Formal in-app deletion and retention controls are planned before any broader multi-user release.",
  },
  {
    title: "Contact",
    body: "Questions about this privacy policy or data handling can be sent to dustin.varcoe@outlook.com.",
  },
];

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function formatMoney(cents: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

function formatAxis(value: number) {
  const dollars = Number(value) / 100;
  const absoluteDollars = Math.abs(dollars);
  const sign = dollars < 0 ? "-" : "";
  if (absoluteDollars >= 1_000_000) return `${sign}$${(absoluteDollars / 1_000_000).toFixed(1)}m`;
  if (absoluteDollars >= 1_000) return `${sign}$${Math.round(absoluteDollars / 1_000)}k`;
  return `${sign}$${Math.round(absoluteDollars)}`;
}

function toCents(dollars: number) {
  return Math.round((Number.isFinite(dollars) ? dollars : 0) * 100);
}

function fromCents(cents: number) {
  return Math.round(cents / 100);
}

function addMonths(date: Date, months: number) {
  const next = new Date(date);
  next.setMonth(next.getMonth() + months);
  return next;
}

function parseDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

function monthKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(date: Date) {
  return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

function shortDateLabel(value: string) {
  return parseDate(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
}

function formatCategoryName(value: string) {
  return value.replace(/_/g, " ").toLowerCase();
}

function monthKeyLabel(value: string) {
  return parseDate(`${value}-01`).toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

function accountSum(accounts: FinanceAccount[], predicate: (account: FinanceAccount) => boolean) {
  return accounts.filter(predicate).reduce((total, account) => total + account.currentBalanceCents, 0);
}

function PlaidConnector({ enabled, onConnected }: { enabled: boolean; onConnected: () => void }) {
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function prepareLink() {
    setError("");
    try {
      const response = await apiRequest<{ link_token: string }>("/plaid/link-token", { method: "POST" });
      setLinkToken(response.link_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plaid Link could not be prepared");
    }
  }

  const plaid = usePlaidLink({
    token: linkToken,
    onSuccess: async (publicToken) => {
      await apiRequest("/plaid/exchange-public-token", {
        method: "POST",
        body: JSON.stringify({ public_token: publicToken }),
      });
      setLinkToken(null);
      onConnected();
    },
    onExit: () => setLinkToken(null),
  });

  useEffect(() => {
    if (linkToken && plaid.ready) plaid.open();
  }, [linkToken, plaid]);

  return (
    <div className="button-row">
      <button type="button" disabled={!enabled} onClick={prepareLink}>
        Connect Sandbox
      </button>
      {error && <span className="error-text">{error}</span>}
    </div>
  );
}

function PrivacyPolicyDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="privacy-modal" role="dialog" aria-modal="true" aria-labelledby="privacy-title">
        <div className="panel-heading">
          <div>
            <p>Privacy Policy</p>
            <h2 id="privacy-title">TaskBrain Finance</h2>
          </div>
          <button type="button" className="text-button" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="policy-date">Last updated June 10, 2026</p>
        <div className="policy-content">
          {privacyPolicySections.map((section) => (
            <article key={section.title}>
              <h3>{section.title}</h3>
              <p>{section.body}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function AuthPanel({
  onSession,
  onPrivacy,
}: {
  onSession: (session: SessionResponse) => void;
  onPrivacy: () => void;
}) {
  const [mode, setMode] = useState<"register" | "login">("register");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const endpoint = mode === "register" ? "/auth/register" : "/auth/login";
      const body =
        mode === "register"
          ? { email, display_name: displayName, password, timezone: "America/Chicago" }
          : { email, password };
      const session = await apiRequest<SessionResponse>(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setPassword("");
      onSession(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    }
  }

  return (
    <section className="panel auth-panel">
      <div className="panel-heading">
        <div>
          <p>Local Access</p>
          <h2>{mode === "register" ? "Create User" : "Sign In"}</h2>
        </div>
        <button type="button" className="text-button" onClick={() => setMode(mode === "register" ? "login" : "register")}>
          {mode === "register" ? "Sign in" : "Register"}
        </button>
      </div>

      <form className="auth-form" onSubmit={submit}>
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" />
        </label>
        {mode === "register" && (
          <label>
            Display name
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="name" />
          </label>
        )}
        <label>
          Password
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            minLength={12}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
          />
        </label>
        <button type="submit">{mode === "register" ? "Create User" : "Sign In"}</button>
        {error && <span className="error-text">{error}</span>}
      </form>
      <div className="auth-footer">
        <span>Review how local financial data is handled before connecting accounts.</span>
        <button type="button" className="text-button privacy-link" onClick={onPrivacy}>
          Privacy Policy
        </button>
      </div>
    </section>
  );
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [items, setItems] = useState<PlaidItem[]>([]);
  const [netWorth, setNetWorth] = useState<NetWorthResponse | null>(null);
  const [cashFlow, setCashFlow] = useState<CashFlowResponse | null>(null);
  const [recurringStreams, setRecurringStreams] = useState<RecurringStream[]>([]);
  const [plannedExpenses, setPlannedExpenses] = useState<PlannedExpense[]>([]);
  const [timeline, setTimeline] = useState<Timeline>("year");
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);

  const [monthlyIncome, setMonthlyIncome] = useState(5200);
  const [fixedSpend, setFixedSpend] = useState(2800);
  const [variableSpend, setVariableSpend] = useState(900);
  const [debtPayment, setDebtPayment] = useState(450);
  const [monthlyContribution, setMonthlyContribution] = useState(300);
  const [conservativeRate, setConservativeRate] = useState(4);
  const [baseRate, setBaseRate] = useState(7);
  const [aggressiveRate, setAggressiveRate] = useState(10);

  const [expenseTitle, setExpenseTitle] = useState("Wedding");
  const [expenseDate, setExpenseDate] = useState("2026-09-15");
  const [expenseAmount, setExpenseAmount] = useState(2000);
  const [expenseCategory, setExpenseCategory] = useState("Travel");

  const accounts = netWorth?.accounts ?? [];
  const cashCents = accountSum(accounts, (account) => account.type === "depository" && account.classification === "asset");
  const investmentCents = accountSum(
    accounts,
    (account) => account.type === "investment" || ["401k", "ira", "roth", "roth ira"].includes(account.subtype ?? ""),
  );

  const monthlyNetCents = toCents(monthlyIncome - fixedSpend - variableSpend - debtPayment);
  const timelineLength = timelineMonths[timeline];

  const netWorthSeries = useMemo(() => {
    const currentNetWorth = netWorth?.currentNetWorthCents ?? 0;
    const cutoff = timeline === "all" ? null : addMonths(new Date(), -timelineLength);
    const historicalTrend = (netWorth?.trend ?? []).filter((point) => !cutoff || parseDate(point.date) >= cutoff);
    const historicalSeries =
      historicalTrend.length > 0
        ? historicalTrend.map((point) => ({
            date: shortDateLabel(point.date),
            actual: point.netWorthCents,
            planOnly: null,
            netWorth: null,
          }))
        : [
            {
              date: "Today",
              actual: currentNetWorth,
              planOnly: null,
              netWorth: null,
            },
          ];

    const start = new Date();
    let plannedImpact = 0;
    const forecastSeries = Array.from({ length: timelineLength + 1 }, (_, index) => {
      const date = addMonths(start, index);
      const key = monthKey(date);
      const monthExpenses = plannedExpenses
        .filter((expense) => expense.due_date.startsWith(key))
        .reduce((total, expense) => total + expense.amount_cents, 0);
      plannedImpact += monthExpenses;
      return {
        date: index === 0 ? "Now" : monthLabel(date),
        actual: null,
        netWorth: currentNetWorth + monthlyNetCents * index - plannedImpact,
        planOnly: currentNetWorth + monthlyNetCents * index,
      };
    });

    return [...historicalSeries, ...forecastSeries];
  }, [monthlyNetCents, netWorth?.currentNetWorthCents, netWorth?.trend, plannedExpenses, timeline, timelineLength]);

  const hasActualCashFlow = Boolean(cashFlow?.monthlyCashFlow.some((point) => point.transactionCount > 0));

  const cashFlowSeries = useMemo<CashFlowChartPoint[]>(() => {
    if (cashFlow?.monthlyCashFlow.length && hasActualCashFlow) {
      return cashFlow.monthlyCashFlow.map((point) => ({
        date: monthKeyLabel(point.month),
        income: point.incomeCents,
        expense: point.expenseCents,
        net: point.netCents,
        transactionCount: point.transactionCount,
      }));
    }

    const start = new Date();
    let endingCash = cashCents;
    return Array.from({ length: Math.max(12, timelineLength) }, (_, index) => {
      const date = addMonths(start, index);
      const key = monthKey(date);
      const oneTime = plannedExpenses
        .filter((expense) => expense.due_date.startsWith(key))
        .reduce((total, expense) => total + expense.amount_cents, 0);
      const routineOutflow = toCents(fixedSpend + variableSpend + debtPayment);
      const income = toCents(monthlyIncome);
      const net = income - routineOutflow - oneTime;
      endingCash += net;
      return {
        date: monthLabel(date),
        income,
        routineOutflow,
        oneTime,
        net,
        endingCash,
        transactionCount: 0,
      };
    });
  }, [cashCents, cashFlow?.monthlyCashFlow, debtPayment, fixedSpend, hasActualCashFlow, monthlyIncome, plannedExpenses, timelineLength, variableSpend]);

  const investmentSeries = useMemo(() => {
    const currentYear = new Date().getFullYear();
    const startYear = currentYear - 1;
    const endYear = 2060;

    function startingBalance(rate: number) {
      return Math.round(investmentCents / (1 + rate / 100));
    }

    let conservative = startingBalance(conservativeRate);
    let base = startingBalance(baseRate);
    let aggressive = startingBalance(aggressiveRate);

    return Array.from({ length: endYear - startYear + 1 }, (_, index) => {
      const year = startYear + index;
      if (index > 0) {
        conservative = Math.round(conservative * (1 + conservativeRate / 100) + toCents(monthlyContribution * 12));
        base = Math.round(base * (1 + baseRate / 100) + toCents(monthlyContribution * 12));
        aggressive = Math.round(aggressive * (1 + aggressiveRate / 100) + toCents(monthlyContribution * 12));
      }
      return { year: String(year), conservative, base, aggressive };
    });
  }, [aggressiveRate, baseRate, conservativeRate, investmentCents, monthlyContribution]);

  const recommendations = useMemo(() => {
    const largestExpense = [...plannedExpenses].sort((a, b) => b.amount_cents - a.amount_cents)[0];
    const modeledCashPoints = cashFlowSeries
      .map((point) => point.endingCash ?? cashCents + point.net)
      .filter((value): value is number => Number.isFinite(value));
    const lowPoint = Math.min(...modeledCashPoints, cashCents);
    const recoveryMonths =
      largestExpense && monthlyNetCents > 0 ? Math.ceil(largestExpense.amount_cents / monthlyNetCents) : null;
    const finalBase = investmentSeries[investmentSeries.length - 1]?.base ?? investmentCents;

    return {
      largestExpense,
      lowPoint,
      recoveryMonths,
      monthlySurplus: monthlyNetCents,
      finalBase,
    };
  }, [cashCents, cashFlowSeries, investmentCents, investmentSeries, monthlyNetCents, plannedExpenses]);

  const statusCards = useMemo(
    () => [
      ["Backend", health?.ok ? "Online" : "Checking"],
      ["Security", health?.secure_config_present ? "Ready" : "Needs setup"],
      ["OpenAI", health?.openai_key_configured ? "Ready" : "Needs setup"],
      ["Plaid", health?.plaid_configured ? "Ready" : "Needs setup"],
    ],
    [health],
  );

  async function refresh() {
    setError("");
    try {
      setHealth(await apiRequest<HealthResponse>("/health"));
      try {
        const currentSession = await apiRequest<SessionResponse>("/auth/session");
        setSession(currentSession);
        const itemResponse = await apiRequest<{ items: PlaidItem[] }>("/plaid/items");
        setItems(itemResponse.items);
        setNetWorth(await apiRequest<NetWorthResponse>("/net-worth"));
        setCashFlow(await apiRequest<CashFlowResponse>("/cash-flow?months=12"));
        const recurringResponse = await apiRequest<{ streams: RecurringStream[] }>("/cash-flow/recurring");
        setRecurringStreams(recurringResponse.streams);
        const expenseResponse = await apiRequest<{ expenses: PlannedExpense[] }>("/planning/expenses");
        setPlannedExpenses(expenseResponse.expenses);
      } catch {
        setSession(null);
        setItems([]);
        setNetWorth(null);
        setCashFlow(null);
        setRecurringStreams([]);
        setPlannedExpenses([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Finance API is not reachable");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function runSync() {
    setSyncing(true);
    setError("");
    try {
      await apiRequest("/sync", { method: "POST" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  async function addPlannedExpense(event: React.FormEvent) {
    event.preventDefault();
    if (!expenseTitle || !expenseDate || expenseAmount <= 0) return;
    await apiRequest("/planning/expenses", {
      method: "POST",
      body: JSON.stringify({
        title: expenseTitle,
        due_date: expenseDate,
        amount_cents: toCents(expenseAmount),
        category: expenseCategory || null,
      }),
    });
    setExpenseTitle("");
    setExpenseAmount(0);
    await refresh();
  }

  async function deletePlannedExpense(expenseId: string) {
    await apiRequest(`/planning/expenses/${expenseId}`, { method: "DELETE" });
    await refresh();
  }

  return (
    <main className="finance-shell">
      <header className="finance-header">
        <div>
          <p>TaskBrain</p>
          <h1>Financial Intelligence</h1>
        </div>
        <div className="header-actions">
          <button type="button" className="text-button privacy-link" onClick={() => setPrivacyOpen(true)}>
            Privacy Policy
          </button>
          <div className="timeline-tabs" aria-label="Timeline">
            {(["month", "quarter", "year", "all"] as Timeline[]).map((value) => (
              <button
                key={value}
                type="button"
                className={timeline === value ? "active" : ""}
                onClick={() => setTimeline(value)}
              >
                {value === "all" ? "All" : value[0].toUpperCase() + value.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </header>

      <PrivacyPolicyDialog open={privacyOpen} onClose={() => setPrivacyOpen(false)} />

      <section className="status-grid" aria-label="Finance module status">
        {statusCards.map(([label, value]) => (
          <article key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      {error && <p className="page-error">{error}</p>}

      {!session ? (
          <AuthPanel
            onPrivacy={() => setPrivacyOpen(true)}
            onSession={(nextSession) => {
              setSession(nextSession);
              void refresh();
            }}
          />
      ) : (
        <>
          <section className="summary-grid">
            <article className="metric-panel">
              <span>Net Worth</span>
              <strong>{formatMoney(netWorth?.currentNetWorthCents ?? 0)}</strong>
            </article>
            <article className="metric-panel">
              <span>Cash</span>
              <strong>{formatMoney(cashCents)}</strong>
            </article>
            <article className="metric-panel">
              <span>Investments</span>
              <strong>{formatMoney(investmentCents)}</strong>
            </article>
            <article className="metric-panel">
              <span>{hasActualCashFlow ? "12 Mo Cash Flow" : "Monthly Surplus"}</span>
              <strong className={(hasActualCashFlow ? cashFlow?.netCents ?? 0 : recommendations.monthlySurplus) >= 0 ? "asset-money" : "debt-money"}>
                {formatMoney(hasActualCashFlow ? cashFlow?.netCents ?? 0 : recommendations.monthlySurplus)}
              </strong>
            </article>
          </section>

          <section className="control-grid">
            <section className="panel controls-panel">
              <div className="panel-heading">
                <div>
                  <p>Planning Inputs</p>
                  <h2>Cash Flow</h2>
                </div>
              </div>
              <div className="input-grid">
                <label>
                  Monthly income
                  <input type="number" value={monthlyIncome} onChange={(event) => setMonthlyIncome(Number(event.target.value))} />
                </label>
                <label>
                  Fixed spend
                  <input type="number" value={fixedSpend} onChange={(event) => setFixedSpend(Number(event.target.value))} />
                </label>
                <label>
                  Variable spend
                  <input type="number" value={variableSpend} onChange={(event) => setVariableSpend(Number(event.target.value))} />
                </label>
                <label>
                  Debt payments
                  <input type="number" value={debtPayment} onChange={(event) => setDebtPayment(Number(event.target.value))} />
                </label>
              </div>
            </section>

            <section className="panel controls-panel">
              <div className="panel-heading">
                <div>
                  <p>Scenario Inputs</p>
                  <h2>Investments</h2>
                </div>
              </div>
              <div className="input-grid">
                <label>
                  Monthly contribution
                  <input
                    type="number"
                    value={monthlyContribution}
                    onChange={(event) => setMonthlyContribution(Number(event.target.value))}
                  />
                </label>
                <label>
                  Conservative %
                  <input type="number" value={conservativeRate} onChange={(event) => setConservativeRate(Number(event.target.value))} />
                </label>
                <label>
                  Base %
                  <input type="number" value={baseRate} onChange={(event) => setBaseRate(Number(event.target.value))} />
                </label>
                <label>
                  Aggressive %
                  <input type="number" value={aggressiveRate} onChange={(event) => setAggressiveRate(Number(event.target.value))} />
                </label>
              </div>
            </section>
          </section>

          <section className="chart-grid">
            <section className="panel chart-panel wide-panel">
              <div className="panel-heading">
                <div>
                  <p>Net Worth</p>
                  <h2>Timeline</h2>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={netWorthSeries} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#e6ebf1" vertical={false} />
                  <XAxis dataKey="date" />
                  <YAxis tickFormatter={formatAxis} width={70} />
                  <Tooltip formatter={(value) => formatMoney(Number(value))} />
                  <Legend />
                  <Line type="monotone" dataKey="actual" name="Actual history" stroke="#172033" strokeWidth={2} />
                  <Area type="monotone" dataKey="planOnly" name="Base plan" stroke="#2563eb" fill="#bfdbfe" />
                  <Area type="monotone" dataKey="netWorth" name="After planned expenses" stroke="#0f766e" fill="#99f6e4" />
                </ComposedChart>
              </ResponsiveContainer>
            </section>

            <section className="panel chart-panel">
              <div className="panel-heading">
                <div>
                  <p>Cash Flow</p>
                  <h2>{hasActualCashFlow ? "Actual Monthly Flow" : "Monthly Model"}</h2>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={cashFlowSeries} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#e6ebf1" vertical={false} />
                  <XAxis dataKey="date" />
                  <YAxis tickFormatter={formatAxis} width={70} />
                  <Tooltip formatter={(value) => formatMoney(Number(value))} />
                  <Legend />
                  <Bar dataKey="income" name="Income" fill="#1d4ed8" />
                  {hasActualCashFlow ? (
                    <>
                      <Bar dataKey="expense" name="Expenses" fill="#dc2626" />
                      <Line type="monotone" dataKey="net" name="Net cash flow" stroke="#0f766e" strokeWidth={2} dot={false} />
                    </>
                  ) : (
                    <>
                      <Bar dataKey="routineOutflow" name="Routine outflow" fill="#f59e0b" />
                      <Bar dataKey="oneTime" name="Planned expenses" fill="#dc2626" />
                      <Line type="monotone" dataKey="endingCash" name="Ending cash" stroke="#0f766e" strokeWidth={2} dot={false} />
                    </>
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </section>

            <section className="panel chart-panel">
              <div className="panel-heading">
                <div>
                  <p>Investments</p>
                  <h2>Scenario To 2060</h2>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={investmentSeries} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#e6ebf1" vertical={false} />
                  <XAxis dataKey="year" interval={4} />
                  <YAxis tickFormatter={formatAxis} width={70} />
                  <Tooltip formatter={(value) => formatMoney(Number(value))} />
                  <Legend />
                  <Line type="monotone" dataKey="conservative" name="Conservative" stroke="#64748b" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="base" name="Base" stroke="#2563eb" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="aggressive" name="Aggressive" stroke="#16a34a" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </section>
          </section>

          <section className="planning-grid">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p>Spending</p>
                  <h2>Categories</h2>
                </div>
              </div>
              <div className="category-list">
                {cashFlow?.categories.length ? (
                  cashFlow.categories.map((category) => (
                    <article key={category.category}>
                      <div>
                        <strong>{formatCategoryName(category.category)}</strong>
                        <span>{category.transactionCount} transaction{category.transactionCount === 1 ? "" : "s"}</span>
                      </div>
                      <strong className="debt-money">{formatMoney(category.spentCents)}</strong>
                    </article>
                  ))
                ) : (
                  <span>No category spending yet.</span>
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p>Recurring</p>
                  <h2>Streams</h2>
                </div>
              </div>
              <div className="stream-list">
                {recurringStreams.length ? (
                  recurringStreams.slice(0, 8).map((stream) => (
                    <article key={stream.id}>
                      <div>
                        <strong>{stream.merchantName || stream.description}</strong>
                        <span>
                          {[stream.direction, stream.frequency, stream.nextExpectedDate ? `next ${stream.nextExpectedDate}` : null]
                            .filter(Boolean)
                            .join(" / ")}
                        </span>
                      </div>
                      <strong className={stream.direction === "inflow" ? "asset-money" : "debt-money"}>
                        {formatMoney(Math.abs(stream.averageAmountCents))}
                      </strong>
                    </article>
                  ))
                ) : (
                  <span>No recurring streams yet.</span>
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p>Future Expenses</p>
                  <h2>Events</h2>
                </div>
              </div>
              <form className="expense-form" onSubmit={addPlannedExpense}>
                <input value={expenseTitle} onChange={(event) => setExpenseTitle(event.target.value)} placeholder="Expense" />
                <input value={expenseDate} onChange={(event) => setExpenseDate(event.target.value)} type="date" />
                <input value={expenseAmount} onChange={(event) => setExpenseAmount(Number(event.target.value))} type="number" min="1" />
                <input value={expenseCategory} onChange={(event) => setExpenseCategory(event.target.value)} placeholder="Category" />
                <button type="submit">Add</button>
              </form>
              <div className="expense-list">
                {plannedExpenses.length === 0 ? (
                  <span>No planned expenses.</span>
                ) : (
                  plannedExpenses.map((expense) => (
                    <article key={expense.id}>
                      <div>
                        <strong>{expense.title}</strong>
                        <span>{expense.due_date} · {expense.category || "Uncategorized"}</span>
                      </div>
                      <div>
                        <strong>{formatMoney(expense.amount_cents)}</strong>
                        <button type="button" className="text-button danger-text" onClick={() => void deletePlannedExpense(expense.id)}>
                          Remove
                        </button>
                      </div>
                    </article>
                  ))
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p>Review</p>
                  <h2>Plan Notes</h2>
                </div>
              </div>
              <div className="recommendation-list">
                <article>
                  <strong>Monthly buffer</strong>
                  <span>{formatMoney(recommendations.monthlySurplus)}</span>
                </article>
                <article>
                  <strong>Lowest modeled cash</strong>
                  <span>{formatMoney(recommendations.lowPoint)}</span>
                </article>
                <article>
                  <strong>Largest event recovery</strong>
                  <span>
                    {recommendations.largestExpense && recommendations.recoveryMonths
                      ? `${recommendations.largestExpense.title}: ${recommendations.recoveryMonths} month${recommendations.recoveryMonths === 1 ? "" : "s"}`
                      : "Add surplus and events"}
                  </span>
                </article>
                <article>
                  <strong>Base 2060 investments</strong>
                  <span>{formatMoney(recommendations.finalBase)}</span>
                </article>
              </div>
            </section>

            <section className="panel wide-panel">
              <div className="panel-heading">
                <div>
                  <p>Transactions</p>
                  <h2>Recent Activity</h2>
                </div>
              </div>
              <div className="transaction-list">
                {cashFlow?.recentTransactions.length ? (
                  cashFlow.recentTransactions.map((transaction) => (
                    <article key={transaction.id}>
                      <div>
                        <strong>{transaction.description}</strong>
                        <span>
                          {transaction.postedDate} / {formatCategoryName(transaction.category)}
                        </span>
                      </div>
                      <strong className={transaction.cashFlowCents >= 0 ? "asset-money" : "debt-money"}>
                        {formatMoney(transaction.cashFlowCents)}
                      </strong>
                    </article>
                  ))
                ) : (
                  <span>No synced transactions yet.</span>
                )}
              </div>
            </section>
          </section>

          <section className="workspace-grid">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p>Plaid Sandbox</p>
                  <h2>Connections</h2>
                </div>
              </div>
              <PlaidConnector enabled={Boolean(health?.plaid_configured)} onConnected={refresh} />
              <div className="button-row sync-block">
                <button type="button" disabled={items.length === 0 || syncing} onClick={runSync}>
                  {syncing ? "Syncing..." : "Sync Sandbox Data"}
                </button>
              </div>
              <div className="item-list">
                {items.map((item) => (
                  <div key={item.item_id}>
                    <strong>{item.status}</strong>
                    <span>{item.last_successful_sync_at ?? item.created_at ?? item.item_id}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel accounts-panel">
              <div className="panel-heading">
                <div>
                  <p>Accounts</p>
                  <h2>Balances</h2>
                </div>
              </div>
              <div className="account-list">
                {accounts.map((account) => (
                  <article key={account.id}>
                    <div>
                      <strong>{account.name}</strong>
                      <span>{[account.type, account.subtype].filter(Boolean).join(" / ")}</span>
                    </div>
                    <div className={account.classification === "debt" ? "debt-money" : "asset-money"}>
                      {formatMoney(account.currentBalanceCents)}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </section>
        </>
      )}
    </main>
  );
}

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("TaskBrain Finance root element was not found");
}

const root = window.taskbrainFinanceRoot ?? createRoot(rootElement);
window.taskbrainFinanceRoot = root;
root.render(<App />);
