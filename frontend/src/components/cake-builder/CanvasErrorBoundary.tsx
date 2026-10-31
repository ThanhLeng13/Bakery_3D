"use client";

import { Component, type ReactNode } from "react";

/** DOM boundary: fallbacks must live outside the Three.js reconciler. */
export default class CanvasErrorBoundary extends Component<{
  children: ReactNode;
  message?: string;
  detail?: string;
}, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <div role="status" className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-6 text-center">
          <p className="text-sm font-medium text-mocha">
            {this.props.message ?? "Không hiển thị được mô hình 3D"}
          </p>
          <p className="text-xs text-mocha/60">
            {this.props.detail ?? "Bạn vẫn có thể tùy chỉnh bánh bằng các nút bên cạnh."}
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
