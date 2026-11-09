import { useEffect, useState } from 'react';

/** Fetch private evidence without putting account credentials in a URL. */
export function useProtectedDocument(source: string | null, token: string) {
  const [result, setResult] = useState<{ source: string; token: string; url: string; error: string } | null>(null);
  useEffect(() => {
    if (!source) return;
    const controller = new AbortController();
    let objectUrl: string | undefined;
    fetch(source, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('This document could not be opened. Refresh the case and try again.');
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setResult({ source, token, url: objectUrl, error: '' });
      })
      .catch(error => {
        if (!controller.signal.aborted) setResult({ source, token, url: '', error: error.message });
      });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [source, token]);
  return result?.source === source && result.token === token ? result : { source: source || '', url: '', error: '' };
}
