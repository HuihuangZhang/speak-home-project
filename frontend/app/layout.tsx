import type { Metadata } from "next";
import "@livekit/components-styles";

export const metadata: Metadata = {
  title: "Speak Home — AI Exercise Tutor",
  description: "Your personal AI fitness coach",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#f5f5f5" }}>
        {children}
      </body>
    </html>
  );
}
