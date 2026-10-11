import React from 'react';
import { safeExternalUrl } from '@/lib/externalUrl';

const URL_PATTERN = /(https?:\/\/[^\s]+)/g;

function trimUrl(value: string): { url: string; trailing: string } {
  const match = value.match(/^(.*?)([),.!?;:]*)$/);
  return match ? { url: match[1], trailing: match[2] } : { url: value, trailing: '' };
}

/** Render server-sanitised announcement text without ever interpreting HTML. */
export function AnnouncementBody({ body }: { body: string }) {
  const lines = body.split('\n');
  return (
    <p className="whitespace-pre-wrap break-words text-sm leading-6 text-[var(--text-muted)]">
      {lines.map((line, lineIndex) => {
        const pieces = line.split(URL_PATTERN);
        return (
          <React.Fragment key={`line-${lineIndex}`}>
            {pieces.map((piece, pieceIndex) => {
              if (!/^https?:\/\//i.test(piece)) return <React.Fragment key={`text-${pieceIndex}`}>{piece}</React.Fragment>;
              const { url, trailing } = trimUrl(piece);
              const safeUrl = safeExternalUrl(url);
              if (!safeUrl) return <React.Fragment key={`unsafe-${pieceIndex}`}>{piece}</React.Fragment>;
              return (
                <React.Fragment key={`link-${pieceIndex}`}>
                  <a
                    className="break-all text-[var(--accent-bright)] underline underline-offset-2 hover:text-[var(--text)]"
                    href={safeUrl}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    {url}
                  </a>
                  {trailing}
                </React.Fragment>
              );
            })}
            {lineIndex < lines.length - 1 && '\n'}
          </React.Fragment>
        );
      })}
    </p>
  );
}
