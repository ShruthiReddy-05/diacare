import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { QuestionDefinition, LanguageCode } from '../../domain/types';

interface Message {
  id: string;
  role: 'bot' | 'user';
  text: string;
}

interface Props {
  messages: Message[];
  currentQuestion: QuestionDefinition | null;
  language: LanguageCode;
}

function ChatBubble({ msg }: { msg: Message }) {
  return (
    <motion.div
      className={`chat-bubble ${msg.role}`}
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.25 }}
    >
      <div className="bubble-content">{msg.text}</div>
    </motion.div>
  );
}

export default function ChatWindow({ messages, currentQuestion, language }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentQuestion]);

  return (
    <div className="chat-window">
      <div className="chat-scroll">
        <AnimatePresence>
          {messages.map((msg) => (
            <ChatBubble key={msg.id} msg={msg} />
          ))}
        </AnimatePresence>

        {currentQuestion && (
          <motion.div
            className="chat-bubble bot"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            key={currentQuestion.id}
          >
            <div className="bubble-content" dangerouslySetInnerHTML={{ __html: currentQuestion.prompt[language] }} />
          </motion.div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
