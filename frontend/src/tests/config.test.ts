import { describe, it, expect } from "vitest";
import { getApiBaseUrl, getWebSocketUrl } from "../services/config";

describe("Configuration and URL Resolvers", () => {
  describe("getApiBaseUrl", () => {
    it("defaults to /api when undefined or empty", () => {
      expect(getApiBaseUrl()).toBe("/api");
      expect(getApiBaseUrl("")).toBe("/api");
      expect(getApiBaseUrl("   ")).toBe("/api");
    });

    it("normalizes trailing slashes and appends /api to origin", () => {
      expect(getApiBaseUrl("http://localhost:8000")).toBe("http://localhost:8000/api");
      expect(getApiBaseUrl("http://localhost:8000/")).toBe("http://localhost:8000/api");
      expect(getApiBaseUrl("https://api.example.com///")).toBe("https://api.example.com/api");
    });

    it("does not duplicate /api when already present", () => {
      expect(getApiBaseUrl("http://localhost:8000/api")).toBe("http://localhost:8000/api");
      expect(getApiBaseUrl("http://localhost:8000/api/")).toBe("http://localhost:8000/api");
      expect(getApiBaseUrl("https://api.example.com/api")).toBe("https://api.example.com/api");
      expect(getApiBaseUrl("/api")).toBe("/api");
    });
  });

  describe("getWebSocketUrl", () => {
    const mockLocHttp = { protocol: "http:", host: "localhost:5173" };
    const mockLocHttps = { protocol: "https:", host: "app.blindbillion.com" };

    it("derives ws URL from location when env is unset", () => {
      const url = getWebSocketUrl("abcd", "tok-123", undefined, mockLocHttp);
      expect(url).toBe("ws://localhost:5173/ws/rooms/ABCD?token=tok-123");
    });

    it("derives wss URL when location is https", () => {
      const url = getWebSocketUrl("xyz9", "tok-abc", "", mockLocHttps);
      expect(url).toBe("wss://app.blindbillion.com/ws/rooms/XYZ9?token=tok-abc");
    });

    it("normalizes env ws URL with ws protocol", () => {
      const url = getWebSocketUrl("ROOM1", "tok", "ws://127.0.0.1:8000", mockLocHttp);
      expect(url).toBe("ws://127.0.0.1:8000/ws/rooms/ROOM1?token=tok");
    });

    it("converts http to ws and https to wss", () => {
      const url1 = getWebSocketUrl("ROOM1", "tok", "http://backend:8000", mockLocHttp);
      expect(url1).toBe("ws://backend:8000/ws/rooms/ROOM1?token=tok");

      const url2 = getWebSocketUrl("ROOM1", "tok", "https://backend.example.com", mockLocHttps);
      expect(url2).toBe("wss://backend.example.com/ws/rooms/ROOM1?token=tok");
    });

    it("handles trailing slashes and explicit /ws path", () => {
      const url = getWebSocketUrl("room1", "tok", "ws://127.0.0.1:8000/ws/", mockLocHttp);
      expect(url).toBe("ws://127.0.0.1:8000/ws/rooms/ROOM1?token=tok");
    });
  });
});
