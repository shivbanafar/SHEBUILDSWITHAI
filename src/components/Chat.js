import React, { useState, useEffect, useCallback, useRef } from "react";
import io from "socket.io-client";
import { Plus } from "lucide-react";
import "./PRChatbot.css";

const SOCKET_URL = "http://localhost:3000";

const PRChatbot = () => {
  const [prompt, setPrompt] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [socket, setSocket] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const newSocket = io(SOCKET_URL, {
      transports: ["websocket", "polling"],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 10000,
    });

    newSocket.on("connect", () => {
      console.log("Connected to server");
    });

    newSocket.on("connect_error", (error) => {
      setError("Failed to connect to the server. Please try again later.");
      console.error("Connection error:", error);
    });

    newSocket.on("disconnect", (reason) => {
      console.log("Disconnected:", reason);
    });

    newSocket.on("chatbot_response", (data) => {
      const newMessage = {
        sender: "Dumbfuck Bot",
        message: data.response,
      };
      setChatMessages((prevMessages) => [...prevMessages, newMessage]);
      setIsLoading(false);
    });

    newSocket.on("chatbot_error", (errorMessage) => {
      setError(errorMessage);
      setIsLoading(false);
    });

    newSocket.on("image_received", (imagePath) => {
      const newMessage = {
        sender: "You",
        message: `<img src="${imagePath}" alt="Uploaded" style="max-width: 300px;" />`,
        isImage: true
      };
      setChatMessages((prevMessages) => [...prevMessages, newMessage]);
      setIsLoading(false);
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  const handleSendMessage = useCallback(() => {
    if (prompt.trim() === "") return;

    setIsLoading(true);
    setError(null);

    setChatMessages((prevMessages) => [
      ...prevMessages,
      { sender: "You", message: prompt },
    ]);

    socket.emit("chatbot_message", prompt);

    setPrompt("");
  }, [prompt, socket]);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;
  
    setIsLoading(true);
    setError(null);
  
    const reader = new FileReader();
    reader.onloadend = () => {
      // Send only the base64 data part of the DataURL
      const base64Data = reader.result.split(',')[1];
      socket.emit("image_upload", { data: base64Data, type: file.type });
    };
    reader.onerror = () => {
      setError("Failed to read the image file");
      setIsLoading(false);
    };
    reader.readAsDataURL(file);
  };

  const handlePlusClick = () => {
    fileInputRef.current?.click();
  };

  const renderMessage = (message, isImage) => {
    if (isImage) {
      return <div dangerouslySetInnerHTML={{ __html: message }} />;
    }
    return message.split("\n").map((line, index) => (
      <React.Fragment key={index}>
        {line}
        <br />
      </React.Fragment>
    ));
  };

  return (
    <div className="prchatbot-app-container">
      <div className="prchatbot-container">
        <div className="prchatbot-header">
          <h1>Chat Assistant</h1>
          <input
            type="text"
            className="prchatbot-search-bar"
            placeholder="Search in chat"
          />
        </div>
        <div
          className="prchatbot-messages"
          style={{ maxHeight: "70vh", overflowY: "auto" }}
        >
          {chatMessages.map((msg, index) => (
            <div
              key={index}
              className={`prchatbot-message ${msg.sender.toLowerCase()}`}
            >
              <strong>{msg.sender}:</strong> {renderMessage(msg.message, msg.isImage)}
            </div>
          ))}
          {error && (
            <div className="prchatbot-error-message">
              {error}
              <button onClick={() => handleSendMessage()}>Retry</button>
            </div>
          )}
        </div>
        <div className="prchatbot-input">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
            placeholder="Ask a question..."
            disabled={isLoading}
          />
          <input
            type="file"
            ref={fileInputRef}
            accept="image/*"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <button 
            className="prchatbot-upload-btn"
            onClick={handlePlusClick}
            disabled={isLoading}
          >
            <Plus size={24} />
          </button>
          <button 
            className="prchatbot-send-btn"
            onClick={handleSendMessage} 
            disabled={isLoading}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default PRChatbot;

// import React, { useState, useEffect, useCallback } from "react";
// import io from "socket.io-client";
// import "./PRChatbot.css";

// const SOCKET_URL = "http://localhost:3000";

// const PRChatbot = () => {
//   const [prompt, setPrompt] = useState("");
//   const [chatMessages, setChatMessages] = useState([]);
//   const [socket, setSocket] = useState(null);
//   const [isLoading, setIsLoading] = useState(false);
//   const [error, setError] = useState(null);

//   useEffect(() => {
//     const newSocket = io(SOCKET_URL, {
//       transports: ["websocket", "polling"],
//       reconnectionAttempts: 5,
//       reconnectionDelay: 1000,
//       timeout: 10000,
//     });

//     newSocket.on("connect", () => {
//       console.log("Connected to server");
//     });

//     newSocket.on("connect_error", (error) => {
//       setError("Failed to connect to the server. Please try again later.");
//       console.error("Connection error:", error);
//     });

//     newSocket.on("disconnect", (reason) => {
//       console.log("Disconnected:", reason);
//     });

//     newSocket.on("chatbot_response", (data) => {
//       const newMessage = {
//         sender: "Dumbfuck Bot",
//         message: data.response,
//       };
//       setChatMessages((prevMessages) => [...prevMessages, newMessage]);
//       setIsLoading(false);
//     });

//     newSocket.on("chatbot_error", (errorMessage) => {
//       setError(errorMessage);
//       setIsLoading(false);
//     });

//     setSocket(newSocket);

//     return () => {
//       newSocket.close();
//     };
//   }, []);

//   const handleSendMessage = useCallback(() => {
//     if (prompt.trim() === "") return;

//     setIsLoading(true);
//     setError(null);

//     setChatMessages((prevMessages) => [
//       ...prevMessages,
//       { sender: "You", message: prompt },
//     ]);

//     socket.emit("chatbot_message", prompt);

//     setPrompt("");
//   }, [prompt, socket]);

//   const renderMessage = (message) => {
//     return message.split("\n").map((line, index) => (
//       <React.Fragment key={index}>
//         {line}
//         <br />
//       </React.Fragment>
//     ));
//   };

//   return (
//     <div className="prchatbot-app-container">
//       <div className="prchatbot-container">
//         <div className="prchatbot-header">
//           <h1>Chat Assistant</h1>
//           <input
//             type="text"
//             className="prchatbot-search-bar"
//             placeholder="Search in chat"
//           />
//         </div>
//         <div
//           className="prchatbot-messages"
//           style={{ maxHeight: "70vh", overflowY: "auto" }}
//         >
//           {chatMessages.map((msg, index) => (
//             <div
//               key={index}
//               className={`prchatbot-message ${msg.sender.toLowerCase()}`}
//             >
//               <strong>{msg.sender}:</strong> {renderMessage(msg.message)}
//             </div>
//           ))}
//           {error && (
//             <div className="prchatbot-error-message">
//               {error}
//               <button onClick={() => handleSendMessage()}>Retry</button>
//             </div>
//           )}
//         </div>
//         <div className="prchatbot-input">
//           <input
//             type="text"
//             value={prompt}
//             onChange={(e) => setPrompt(e.target.value)}
//             onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
//             placeholder="Ask a question..."
//             disabled={isLoading}
//           />
//           <button onClick={handleSendMessage} disabled={isLoading}>
//             Send
//           </button>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default PRChatbot;