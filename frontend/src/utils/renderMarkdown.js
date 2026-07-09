/**
 * Shared markdown renderer utilities for AI-generated content.
 * Handles: bold (**text**), italic (*text*), inline code (`code`),
 * numbered lists (1. item), bullet lists (- item), headings (## text).
 * Also strips <think>...</think> blocks from reasoning models.
 */
import React from 'react';
import { Box, Typography } from '@mui/material';

/** Strip <think>...</think> blocks (defensive — backend should already do this). */
export function stripThinkTags(text) {
  return (text || '').replace(/<think>[\s\S]*?<\/think>/g, '').trim();
}

/**
 * Normalize AI-generated content to plain newline-separated text.
 * Models sometimes return recommended_actions as a JSON set/array:
 *   {"1. Do this.","2. Do that."} or ["1. Do this.","2. Do that."]
 * This converts those formats to "1. Do this.\n2. Do that."
 */
function preprocessContent(content) {
  if (!content) return '';
  const s = content.trim();

  // Detect JSON-set { } or JSON-array [ ] wrapping items with commas
  const isSet = s.startsWith('{') && s.endsWith('}');
  const isArr = s.startsWith('[') && s.endsWith(']');

  if (isSet || isArr) {
    // Replace outer braces with brackets so JSON.parse works for both
    const normalized = isSet ? '[' + s.slice(1, -1) + ']' : s;
    try {
      const parsed = JSON.parse(normalized);
      if (Array.isArray(parsed)) {
        return parsed.map(item => String(item)).join('\n');
      }
    } catch (_) {
      // JSON.parse failed — try splitting on "," boundary manually
      // Handles: {"1. Foo.","2. Bar."} even when items contain commas
      const inner = s.slice(1, -1);
      const parts = inner.split(/","|",\s*"|'\s*,\s*'/);
      if (parts.length > 1) {
        return parts.map(p => p.replace(/^"|"$/g, '').trim()).join('\n');
      }
    }
  }

  return s;
}

/** Parse a line of text into bold/italic/code/plain segments. */
function parseInline(text) {
  const parts = [];
  // Match **bold**, *italic*, `code` — in that priority order
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) {
      parts.push({ type: 'text', content: text.slice(last, match.index) });
    }
    const m = match[0];
    if (m.startsWith('**')) {
      parts.push({ type: 'bold', content: m.slice(2, -2) });
    } else if (m.startsWith('*')) {
      parts.push({ type: 'italic', content: m.slice(1, -1) });
    } else {
      parts.push({ type: 'code', content: m.slice(1, -1) });
    }
    last = match.index + m.length;
  }
  if (last < text.length) {
    parts.push({ type: 'text', content: text.slice(last) });
  }
  return parts;
}

/** Render a line with inline markdown (bold, italic, code). */
export function InlineContent({ text }) {
  return (
    <>
      {parseInline(text || '').map((p, i) => {
        if (p.type === 'bold') return <strong key={i}>{p.content}</strong>;
        if (p.type === 'italic') return <em key={i}>{p.content}</em>;
        if (p.type === 'code') return (
          <code key={i} style={{
            background: 'rgba(0,0,0,0.35)',
            padding: '1px 5px',
            borderRadius: 3,
            fontFamily: 'monospace',
            fontSize: '0.82em',
          }}>
            {p.content}
          </code>
        );
        return <span key={i}>{p.content}</span>;
      })}
    </>
  );
}

/**
 * Render a full AI message/text block with markdown formatting.
 * Handles paragraphs, numbered lists, bullet lists, and headings.
 *
 * @param {string} content - Raw AI text (may contain markdown)
 * @param {string} textVariant - MUI Typography variant (default 'body2')
 * @param {object} textSx - Additional sx props for text nodes
 */
export function FormattedMessage({ content, textVariant = 'body2', textSx = {} }) {
  const clean = preprocessContent(stripThinkTags(content || ''));
  const lines = clean.split('\n');
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip blank lines (spacing handled by gap/mb)
    if (!trimmed) {
      i++;
      continue;
    }

    // Numbered list — collect consecutive numbered items
    if (/^\d+\.\s/.test(trimmed)) {
      const items = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        const m = t.match(/^\d+\.\s+([\s\S]+)/);
        if (m) {
          items.push(m[1]);
          i++;
        } else if (!t) {
          i++;
          break;
        } else {
          break;
        }
      }
      elements.push(
        <Box
          key={elements.length}
          component="ol"
          sx={{ pl: 2.5, my: 0.5, '& li': { mb: 0.5 } }}
        >
          {items.map((item, j) => (
            <li key={j}>
              <Typography variant={textVariant} component="span" sx={{ lineHeight: 1.65, ...textSx }}>
                <InlineContent text={item} />
              </Typography>
            </li>
          ))}
        </Box>
      );
      continue;
    }

    // Bullet list — collect consecutive bullet items
    if (/^[-*•]\s/.test(trimmed)) {
      const items = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        const m = t.match(/^[-*•]\s+([\s\S]+)/);
        if (m) {
          items.push(m[1]);
          i++;
        } else if (!t) {
          i++;
          break;
        } else {
          break;
        }
      }
      elements.push(
        <Box
          key={elements.length}
          component="ul"
          sx={{ pl: 2.5, my: 0.5, '& li': { mb: 0.5 } }}
        >
          {items.map((item, j) => (
            <li key={j}>
              <Typography variant={textVariant} component="span" sx={{ lineHeight: 1.65, ...textSx }}>
                <InlineContent text={item} />
              </Typography>
            </li>
          ))}
        </Box>
      );
      continue;
    }

    // Headings (##, ###)
    const headingMatch = trimmed.match(/^#{1,3}\s+([\s\S]+)/);
    if (headingMatch) {
      elements.push(
        <Typography
          key={elements.length}
          variant="subtitle2"
          sx={{ fontWeight: 700, mt: 1, mb: 0.25, lineHeight: 1.4 }}
        >
          <InlineContent text={headingMatch[1]} />
        </Typography>
      );
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <Typography
        key={elements.length}
        variant={textVariant}
        sx={{ lineHeight: 1.65, mb: 0.25, ...textSx }}
      >
        <InlineContent text={trimmed} />
      </Typography>
    );
    i++;
  }

  return <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.1 }}>{elements}</Box>;
}
