"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="my-12 mx-auto max-w-lg rounded-lg border border-red-200 bg-card p-6 text-center shadow-sm">
      <h1 className="text-2xl font-bold text-navy">Something went wrong</h1>
      <p className="mt-2 text-sm text-gray-600">
        This page hit an unexpected error while loading its data.
      </p>
      <div className="mt-4 flex justify-center gap-4 text-sm">
        <button
          type="button"
          onClick={() => {
            window.location.hash = "";
            reset();
          }}
          className="rounded-lg bg-navy px-4 py-2 font-medium text-white hover:bg-navy-light transition-colors"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded-lg border border-border px-4 py-2 font-medium text-navy-light hover:text-gold transition-colors"
        >
          Home
        </Link>
      </div>
    </div>
  );
}
