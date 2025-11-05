import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { JetBrains_Mono } from "next/font/google";
import { Outfit } from "next/font/google";
import "@fontsource/geist";
import "@fontsource/jetbrains-mono";
import "@fontsource/outfit";
import "./globals.css";

const geistSans = Geist({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-geist-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});

const outfit = Outfit({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-outfit",
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000",
  ),
  title: "WEB BUILDER AI",
  description: "Build React applications with AI",
  icons: {
    icon: "/logo.png",
  },
  openGraph: {
    title: "WEB BUILDER AI ",
    description:
      "Build applications faster with AI-powered code generation and intelligent development assistance.",
    images: [
      {
        url: "/logo.png",
        width: 1200,
        height: 630,
        alt: "WEB BUILDER AI Logo",
      },
    ],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "WEB BUILDER AI",
    description:
      "Build applications faster with AI-powered code generation and intelligent development assistance.",
    images: ["/logo.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${jetbrainsMono.variable} ${outfit.variable} font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
