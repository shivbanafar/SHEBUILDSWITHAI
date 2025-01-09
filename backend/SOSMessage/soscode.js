const express = require('express');
const axios = require('axios');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const cors = require('cors');
require('dotenv').config();

// Validate environment variables
if (!process.env.FAST2SMS_API_KEY) {
    console.error('FAST2SMS_API_KEY is required');
    process.exit(1);
}

const app = express();

// Security middleware
app.use(helmet());
app.use(cors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || 'http://localhost:3000'
}));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
});
app.use(limiter);

// Body parser with limits
app.use(express.json({ limit: '10kb' }));
app.use(express.static('public', {
    maxAge: '1h',
    setHeaders: (res, path) => {
        res.setHeader('X-Content-Type-Options', 'nosniff');
    }
}));

// Phone number validation
const validatePhoneNumber = (phone) => {
    const phoneRegex = /^\d{10}$/;  // Adjust regex based on your requirements
    return phoneRegex.test(phone);
};

// Message validation
const validateMessage = (message) => {
    return message.length <= 160 && message.length > 0;
};

// Send SOS route
app.post('/api/send-sos', async (req, res) => {
    const { contacts, message } = req.body;
    const defaultMessage = "Emergency! I need help! This is an SOS alert.";
    const finalMessage = message || defaultMessage;

    try {
        // Input validation
        if (!Array.isArray(contacts) || contacts.length === 0) {
            return res.status(400).json({ error: 'Invalid or empty contacts array' });
        }

        if (contacts.length > 10) {
            return res.status(400).json({ error: 'Too many contacts. Maximum 10 allowed.' });
        }

        if (!validateMessage(finalMessage)) {
            return res.status(400).json({ error: 'Invalid message length' });
        }

        // Validate all phone numbers first
        const invalidPhones = contacts.filter(contact => !validatePhoneNumber(contact.phone));
        if (invalidPhones.length > 0) {
            return res.status(400).json({ 
                error: 'Invalid phone numbers detected',
                invalidPhones: invalidPhones.map(c => c.phone)
            });
        }

        // Send messages in parallel with timeout
        const sendPromises = contacts.map(contact => 
            axios({
                method: 'POST',
                url: 'https://www.fast2sms.com/dev/bulk',
                headers: {
                    'authorization': process.env.FAST2SMS_API_KEY,
                    'Content-Type': 'application/json'
                },
                data: {
                    "route": "q",
                    "message": finalMessage,
                    "numbers": contact.phone,
                    "language": "english"
                },
                timeout: 5000 // 5 second timeout
            }).catch(error => ({
                phone: contact.phone,
                error: error.message
            }))
        );

        const results = await Promise.all(sendPromises);

        // Process results
        const failures = results.filter(result => result.error);
        const successes = results.filter(result => !result.error);

        res.json({ 
            success: true,
            summary: {
                total: contacts.length,
                successful: successes.length,
                failed: failures.length
            },
            failures: failures.length > 0 ? failures : undefined
        });

    } catch (error) {
        console.error('Error sending SMS:', error);
        res.status(500).json({ 
            error: 'Internal server error',
            // Only send safe error information
            message: 'Failed to process SOS request'
        });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ 
        error: 'Internal server error',
        message: 'Something went wrong'
    });
});

// Start server
const PORT = process.env.PORT || 5020;
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('SIGTERM received. Shutting down gracefully...');
    server.close(() => {
        console.log('Process terminated');
    });
});