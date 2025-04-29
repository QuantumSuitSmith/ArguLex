const express = require('express');
const cors = require('cors');
const { Resend } = require('resend');  

const app = express();
const PORT = 5000;

// Initialize Resend with your API key
const resend = new Resend('re_RJoMWgK8_MYxL9PEa1Di59Bmx5vwJMhq9');

app.use(cors());
app.use(express.json());

// Simple test route
app.get('/', (req, res) => {
  res.send('Server is running!');
});

// Route to send OTP
app.post('/send-otp', async (req, res) => {
  const { email } = req.body;

  if (!email) {
    return res.status(400).json({ error: 'Email is required' });
  }

  const otp = Math.floor(100000 + Math.random() * 900000); 

  try {
    await resend.emails.send({
      from: 'chintalaakshay030@gmail.com', // Sender address default
      to: email,
      subject: 'Your OTP Code',
      html: `<p>Your OTP code is: <strong>${otp}</strong></p>`, 
    });

    res.status(200).json({ message: 'OTP sent successfully', otp: otp });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Failed to send OTP' });
  }
});


app.listen(PORT, () => {
  console.log(`Server started on http://localhost:${PORT}`); 
});
