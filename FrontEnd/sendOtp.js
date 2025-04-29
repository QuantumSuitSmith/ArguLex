import Resend from "resend";

const resend = new Resend("re_Bsvuqcpj_2De6xJvN28EBSnd91QCakTR7");

// Function to send OTP email
export async function sendOtpEmail(email, otp) {
  try {
    const data = await resend.emails.send({
      from: "chintalaakshay030@gmail.com", 
      to: email,
      subject: "Your OTP Code",
      html: `<p>Your OTP code is <strong>${otp}</strong>. It expires in 10 minutes.</p>`,
    });

    console.log("Email sent", data);
    return data;
  } catch (error) {
    console.error("Error sending email:", error);
    throw error;
  }
}
