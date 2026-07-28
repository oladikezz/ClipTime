import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClipTime — локальная студия коротких видео",
  description: "Создание вертикальных клипов с размытым фоном и динамическими субтитрами.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body>{children}</body></html>;
}
