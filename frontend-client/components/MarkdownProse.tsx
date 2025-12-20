"use client"

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'

interface MarkdownProseProps {
  content: string | null | undefined
  className?: string
}

export function MarkdownProse({ content, className = "" }: MarkdownProseProps) {
  if (!content) {
    return null
  }

  return (
    <div className={`prose prose-lg max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          // Images: responsive, rounded, with spacing
          img: ({ node, ...props }) => (
            <img
              {...props}
              className="w-full rounded-xl my-6"
              alt={props.alt || ""}
            />
          ),
          // Links: blue, hover underline, external
          a: ({ node, ...props }) => {
            const href = props.href || ""
            const isVideoLink = /\.(mp4|webm|ogg)$/i.test(href)
            
            // If it's a video link, render as video element
            if (isVideoLink) {
              return (
                <video
                  src={href}
                  controls
                  className="w-full rounded-xl my-6"
                >
                  Your browser does not support the video tag.
                </video>
              )
            }
            
            // Regular link
            return (
              <a
                {...props}
                className="text-blue-600 hover:underline"
                target="_blank"
                rel="noreferrer"
              />
            )
          },
          // Blockquotes: left border, italic, padding
          blockquote: ({ node, ...props }) => (
            <blockquote
              {...props}
              className="border-l-4 border-gray-300 pl-4 italic text-slate-600 my-6"
            />
          ),
          // Code blocks: basic styling
          code: ({ node, className, ...props }: any) => {
            const isInline = !className
            if (isInline) {
              return (
                <code
                  {...props}
                  className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm font-mono"
                />
              )
            }
            return (
              <code
                {...props}
                className="block bg-gray-100 text-gray-800 p-4 rounded-lg overflow-x-auto my-4"
              />
            )
          },
          // Paragraphs: check if they contain only video links
          p: ({ node, ...props }: any) => {
            const children = props.children
            if (typeof children === 'string' && /\.(mp4|webm|ogg)$/i.test(children)) {
              return (
                <video
                  src={children}
                  controls
                  className="w-full rounded-xl my-6"
                >
                  Your browser does not support the video tag.
                </video>
              )
            }
            return <p {...props} className="my-4" />
          },
          // Headings: better spacing
          h1: ({ node, ...props }) => <h1 {...props} className="text-3xl font-bold mt-8 mb-4" />,
          h2: ({ node, ...props }) => <h2 {...props} className="text-2xl font-bold mt-6 mb-3" />,
          h3: ({ node, ...props }) => <h3 {...props} className="text-xl font-bold mt-4 mb-2" />,
          // Lists: better spacing
          ul: ({ node, ...props }) => <ul {...props} className="list-disc pl-6 my-4" />,
          ol: ({ node, ...props }) => <ol {...props} className="list-decimal pl-6 my-4" />,
          li: ({ node, ...props }) => <li {...props} className="my-2" />,
          // Horizontal rules
          hr: ({ node, ...props }) => <hr {...props} className="my-8 border-gray-300" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

