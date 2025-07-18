'use client';

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import styles from './Chatbot.module.css';
import { getSupabaseClient } from '../../utils/supabaseClient'; // resusing auth client for chatbot user access token
import chatbotAvatar from '../../assets/chatbot.png';
import submit from '../../assets/submit.svg';
import chatbox from '../../assets/chatbox.svg';

type Message = {
  id: number;
  content: string;
  sender: 'You' | 'SwishBot';
};

export default function Chatbot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [sessionId] = useState(() => crypto.randomUUID());

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const supabase = await getSupabaseClient();
        const { data } = await supabase.auth.getSession();
        if (data.session) {
          setAccessToken(data.session.access_token);
        }
      } catch (error) {
        console.error('Error checking auth:', error);
      }
    };
    checkAuth();
  }, []);

  useEffect(() => {
    const handleUnload = async () => {
      try {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        
        if (accessToken) {
          headers['Authorization'] = `Bearer ${accessToken}`;
        }

        await fetch('http://localhost:8081/chat/end_session', {
          method: 'DELETE',
          headers,
          body: JSON.stringify({ session_id: sessionId }),
        });
      } catch {
        console.error('Failed to end session');
      }
    };
    window.addEventListener('beforeunload', handleUnload);
    return () => window.removeEventListener('beforeunload', handleUnload);
  }, [sessionId, accessToken]);

  const handleFakeStreaming = (fullResponse: string) => {
    const chunkSize = 5;
    const totalChunks = Math.ceil(fullResponse.length / chunkSize);
    let currentChunk = 0;
    const interval = setInterval(() => {
      if (currentChunk < totalChunks) {
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage.sender === 'SwishBot') {
            const start = currentChunk * chunkSize;
            const end = Math.min(start + chunkSize, fullResponse.length);
            const updatedMessage = {
              ...lastMessage,
              content: fullResponse.slice(0, end),
            };
            return [...prev.slice(0, -1), updatedMessage];
          }
          return prev;
        });
        currentChunk++;
      } else {
        clearInterval(interval);
      }
    }, 50);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      id: messages.length + 1,
      content: input,
      sender: 'You',
    };
    setMessages([...messages, userMessage]);
    setInput('');
    setThinking(true);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
      }

      const response = await fetch('http://localhost:8081/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: input, session_id: sessionId }),
      });

      const data = await response.json();
      setThinking(false);
      
      if (!data.response) {
        throw new Error(data.detail || 'No response received from server');
      }

      const botMessage: Message = {
        id: messages.length + 2,
        content: '',
        sender: 'SwishBot',
      };
      setMessages((prev) => [...prev, botMessage]);
      handleFakeStreaming(data.response);
    } catch (error) {
      setThinking(false);
      const errorMessage: Message = {
        id: messages.length + 2,
        content:
          "Sorry, I couldn't process your request at this time. Error: " +
          (error instanceof Error ? error.message : String(error)),
        sender: 'SwishBot',
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [isOpen, messages]);

  if (!isOpen) {
    return (
      <button className={styles.chatTrigger} onClick={() => setIsOpen(true)}>
        <img src={chatbotAvatar} alt="" className={styles.triggerIcon} />
        <span className={styles.triggerText}>Ask AI</span>
      </button>
    );
  }

  return (
    <div className={styles.modalOverlay} onClick={() => setIsOpen(false)}>
      <div className={styles.chatWindow} onClick={(e) => e.stopPropagation()}>
        <div className={styles.chatHeader}>
          <img src={chatbotAvatar} alt="Bot" />
          <h2>Ask SwishBot</h2>
        </div>
        <div className={styles.chatMessages}>
          {messages.map((message) => (
            <div
              key={message.id}
              className={`${styles.message} ${
                message.sender === 'You' ? styles.userMessage : ''
              }`}
            >
              <div className={styles.messageHeader}>
                <img src={chatbox} alt={message.sender} />
                <p>{message.sender}</p>
              </div>
              <div className={styles.messageContent}>
                <ReactMarkdown
                  components={{
                    a: ({ node, ...props }) => (
                      <a {...props} target="_blank" rel="noopener noreferrer" />
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
          ))}
          {thinking && (
            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <img src={chatbotAvatar} alt="SwishBot" />
                <p>SwishBot</p>
              </div>
              <div className={`${styles.messageContent} ${styles.typing}`}>
                Thinking
                <div className={styles.loadingDots}>
                  <span className={styles.dot}></span>
                  <span className={styles.dot}></span>
                  <span className={styles.dot}></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className={styles.chatInput}>
          <form onSubmit={handleSubmit} className={styles.inputForm}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask SwishBot a Question"
            />
            <button type="submit" className={styles.submitButton}>
              <img src={submit} alt="Submit" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
