import { useEffect, useRef, useState } from "react";
import * as Y from "yjs";

export class YjsWSProvider {
  private ws: WebSocket | null = null;
  private doc: Y.Doc;
  private projectId: string;
  private token: string;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private connected = false;

  constructor(projectId: string, token: string) {
    this.projectId = projectId;
    this.token = token;
    this.doc = new Y.Doc();
    this.connect();

    this.doc.on("update", (update: Uint8Array, origin: any) => {
      if (origin !== this && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(update);
      }
    });
  }

  private connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/api/v2/projects/${this.projectId}/collab?token=${encodeURIComponent(this.token)}`;
    this.ws = new WebSocket(url);
    this.ws.binaryType = "arraybuffer";

    this.ws.onopen = () => {
      this.connected = true;
      // Send sync step 1
      const stateVector = Y.encodeStateAsUpdate(this.doc);
      this.ws?.send(stateVector);
    };

    this.ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        const update = new Uint8Array(event.data);
        Y.applyUpdate(this.doc, update, this);
      } else if (typeof event.data === "string") {
        // Awareness messages — not implemented yet
      }
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  getDoc() {
    return this.doc;
  }

  destroy() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.ws?.close();
    this.doc.destroy();
  }
}

export function useYjsCollab(projectId: string | undefined) {
  const providerRef = useRef<YjsWSProvider | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    const token = localStorage.getItem("cran_v2_auth_token") || "";
    const provider = new YjsWSProvider(projectId, token);
    providerRef.current = provider;

    const checkReady = setInterval(() => {
      if (provider["connected"]) {
        setReady(true);
        clearInterval(checkReady);
      }
    }, 500);

    return () => {
      clearInterval(checkReady);
      provider.destroy();
      providerRef.current = null;
      setReady(false);
    };
  }, [projectId]);

  return { provider: providerRef.current, ready };
}
