const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");
const path = require("path");
const multer = require("multer");
const fs = require("fs");

const app = express();
app.use(cors());

// Configure multer for image upload
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    const uploadDir = path.join(__dirname, 'uploads');
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir);
    }
    cb(null, uploadDir);
  },
  filename: function (req, file, cb) {
    cb(null, Date.now() + '-' + file.originalname);
  }
});

const upload = multer({ storage: storage });

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"],
  },
});

// Serve static files from the React app
app.use(express.static(path.join(__dirname, "client/build")));
// Serve uploaded files
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Image upload endpoint
app.post("/upload-image", upload.single('image'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }
  const imagePath = `/uploads/${req.file.filename}`;
  io.emit("image_received", imagePath);
  res.json({ imagePath });
});

io.on("connection", (socket) => {
  console.log("A user connected");

  socket.on("image_upload", async (fileData) => {
    try {
      // Convert base64 to buffer
      const buffer = Buffer.from(fileData.data, 'base64');
      
      // Generate a unique filename with proper extension
      const extension = fileData.type.split('/')[1] || 'jpg';
      const filename = `${Date.now()}-upload.${extension}`;
      const uploadDir = path.join(__dirname, 'uploads');
      
      // Create uploads directory if it doesn't exist
      if (!fs.existsSync(uploadDir)) {
        fs.mkdirSync(uploadDir);
      }
      
      // Save the file
      fs.writeFileSync(path.join(uploadDir, filename), buffer);
      
      // Send the image path back to the client
      const imagePath = `/uploads/${filename}`;
      socket.emit("image_received", imagePath);
    } catch (error) {
      console.error("Error handling image upload:", error);
      socket.emit("chatbot_error", "Failed to upload image");
    }
  });

  socket.on("chatbot_message", async (message) => {
    console.log("Message received:", message);

    try {
      const fetch = (await import("node-fetch")).default;
      const flaskResponse = await fetch("http://localhost:5010/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message }),
      });

      if (!flaskResponse.ok) {
        const errorText = await flaskResponse.text();
        throw new Error(
          `HTTP error! status: ${flaskResponse.status}, message: ${errorText}`
        );
      }

      const data = await flaskResponse.json();
      console.log("Flask response:", data);

      socket.emit("chatbot_response", {
        response: data.response,
        product_links: data.product_links,
      });
    } catch (error) {
      console.error("Error fetching chatbot response:", error);
      socket.emit("chatbot_error", `An error occurred while processing your request: ${error.message}`);
    }
  });

  socket.on("disconnect", (reason) => {
    console.log("User disconnected:", reason);
  });
});

// The "catchall" handler: for any request that doesn't
// match one above, send back React's index.html file.
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "client/build", "index.html"));
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`WebSocket server is ready`);
});
// const express = require("express");
// const http = require("http");
// const { Server } = require("socket.io");
// const cors = require("cors");
// const path = require("path");

// const app = express();
// app.use(cors());

// const server = http.createServer(app);
// const io = new Server(server, {
//   cors: {
//     origin: "*",
//     methods: ["GET", "POST"],
//   },
// });

// // Serve static files from the React app
// app.use(express.static(path.join(__dirname, "client/build")));

// io.on("connection", (socket) => {
//   console.log("A user connected");

//   socket.on("chatbot_message", async (message) => {
//     console.log("Message received:", message);

//     try {
//       const fetch = (await import("node-fetch")).default;
//       const flaskResponse = await fetch("http://localhost:5010/ask", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ message: message }),
//       });

//       if (!flaskResponse.ok) {
//         const errorText = await flaskResponse.text();
//         throw new Error(
//           `HTTP error! status: ${flaskResponse.status}, message: ${errorText}`
//         );
//       }

//       const data = await flaskResponse.json();
//       console.log("Flask response:", data);

//       socket.emit("chatbot_response", {
//         response: data.response,
//         product_links: data.product_links,
//       });
//     } catch (error) {
//       console.error("Error fetching chatbot response:", error);
//       socket.emit("chatbot_error", `An error occurred while processing your request: ${error.message}`);
//     }
//   });

//   socket.on("disconnect", (reason) => {
//     console.log("User disconnected:", reason);
//   });
// });

// // The "catchall" handler: for any request that doesn't
// // match one above, send back React's index.html file.
// app.get("*", (req, res) => {
//   res.sendFile(path.join(__dirname, "client/build", "index.html"));
// });

// const PORT = process.env.PORT || 3000;
// server.listen(PORT, () => {
//   console.log(`Server running on port ${PORT}`);
//   console.log(`WebSocket server is ready`);
// });