import { useEffect, useRef } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

interface TerminalProps {
  projectId: string;
}

export default function Terminal({ projectId }: TerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitRef = useRef<FitAddon | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const term = new XTerm({
      fontSize: 13,
      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
      theme: {
        background: "#0c0c0c",
        foreground: "#cccccc",
        cursor: "#cccccc",
        selectionBackground: "#264f78",
        black: "#0c0c0c",
        red: "#c50f1f",
        green: "#13a10e",
        yellow: "#c19c00",
        blue: "#0037da",
        magenta: "#881798",
        cyan: "#3a96dd",
        white: "#cccccc",
      },
      cursorBlink: true,
      convertEol: true,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(container);
    fitAddon.fit();

    termRef.current = term;
    fitRef.current = fitAddon;

    const token = localStorage.getItem("cran_v2_auth_token") || "";
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(
      `${protocol}//${window.location.host}/api/v2/projects/${projectId}/terminal?token=${encodeURIComponent(token)}`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      term.writeln("\x1b[32mConnected to project terminal\x1b[0m\r\n");
    };

    ws.onmessage = (event) => {
      term.write(event.data);
    };

    ws.onclose = () => {
      term.writeln("\r\n\x1b[31mDisconnected\x1b[0m");
    };

    ws.onerror = () => {
      term.writeln("\r\n\x1b[31mConnection error\x1b[0m");
    };

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    const handleResize = () => {
      fitAddon.fit();
      // Optionally send resize to backend
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      ws.close();
      term.dispose();
    };
  }, [projectId]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b bg-card px-3 py-1.5 text-xs font-semibold uppercase text-muted-foreground">
        Terminal
      </div>
      <div ref={containerRef} className="flex-1 overflow-hidden" />
    </div>
  );
}
