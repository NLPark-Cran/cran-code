import { useEffect, useRef, useState } from "react";
import * as Y from "yjs";
import { Awareness, encodeAwarenessUpdate, applyAwarenessUpdate } from "y-protocols/awareness";

export interface LineComment {
  id: string;
  line: number;
  text: string;
  author: string;
  timestamp: number;
}

export class YjsWSProvider {
  private ws: WebSocket | null = null;
  private doc: Y.Doc;
  private awareness: Awareness;
  private projectId: string;
  private token: string;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private connected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;

  constructor(projectId: string, token: string, userInfo: { name: string; color: string }) {
    this.projectId = projectId;
    this.token = token;
    this.doc = new Y.Doc();
    this.awareness = new Awareness(this.doc);
    this.awareness.setLocalStateField("user", userInfo);
    this.connect();

    // Ensure comments map exists
    this.doc.getMap<Y.Array<LineComment>>("comments");

    this.doc.on("update", (update: Uint8Array, origin: any) => {
      if (origin !== this && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(update);
      }
    });

    this.awareness.on("update", ({ added, updated, removed }: any) => {
      const changedClients = added.concat(updated).concat(removed);
      const encoder = new TextEncoder();
      const update = encoder.encode(
        JSON.stringify({
          type: "awareness",
          update: Array.from(encodeAwarenessUpdate(this.awareness, changedClients)),
        })
      );
      if (this.ws?.readyState === WebSocket.OPEN) {
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
      this.reconnectAttempts = 0;
      const stateVector = Y.encodeStateAsUpdate(this.doc);
      this.ws?.send(stateVector);
    };

    this.ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        const data = new Uint8Array(event.data);
        // Try to parse as JSON (awareness)
        try {
          const text = new TextDecoder().decode(data);
          const msg = JSON.parse(text);
          if (msg.type === "awareness" && Array.isArray(msg.update)) {
            applyAwarenessUpdate(this.awareness, new Uint8Array(msg.update), this);
            return;
          }
        } catch {
          // Not JSON, treat as Yjs update
        }
        Y.applyUpdate(this.doc, data, this);
      } else if (typeof event.data === "string") {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "awareness" && Array.isArray(msg.update)) {
            applyAwarenessUpdate(this.awareness, new Uint8Array(msg.update), this);
          }
        } catch {
          // Ignore
        }
      }
    };

    this.ws.onclose = () => {
      this.connected = false;
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error("Yjs WS max reconnect attempts reached");
        return;
      }
      this.reconnectAttempts++;
      const delay = Math.min(3000 * this.reconnectAttempts, 30000);
      this.reconnectTimer = setTimeout(() => this.connect(), delay);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  getDoc() {
    return this.doc;
  }

  getAwareness() {
    return this.awareness;
  }

  /** Get comments for a specific file path */
  getComments(filePath: string): Y.Array<LineComment> {
    const commentsMap = this.doc.getMap<Y.Array<LineComment>>("comments");
    let arr = commentsMap.get(filePath);
    if (!arr) {
      arr = new Y.Array<LineComment>();
      commentsMap.set(filePath, arr);
    }
    return arr;
  }

  /** Add a comment to a file */
  addComment(filePath: string, comment: LineComment): void {
    const arr = this.getComments(filePath);
    arr.push([comment]);
  }

  /** Delete a comment by id */
  deleteComment(filePath: string, id: string): void {
    const arr = this.getComments(filePath);
    const index = arr.toArray().findIndex((c) => c.id === id);
    if (index >= 0) {
      arr.delete(index, 1);
    }
  }

  destroy() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.awareness.destroy();
    this.ws?.close();
    this.doc.destroy();
  }
}

const USER_COLORS = [
  "#ef4444", "#f97316", "#f59e0b", "#84cc16", "#10b981",
  "#06b6d4", "#3b82f6", "#8b5cf6", "#d946ef", "#f43f5e",
];

export function useYjsCollab(projectId: string | undefined, userName: string) {
  const providerRef = useRef<YjsWSProvider | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    const token = localStorage.getItem("cran_v2_auth_token") || "";
    const color = USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)];
    const provider = new YjsWSProvider(projectId, token, { name: userName, color });
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
  }, [projectId, userName]);

  return { provider: providerRef.current, ready };
}
