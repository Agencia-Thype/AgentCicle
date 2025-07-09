/**
 * Trial Banner Component
 *
 * This component shows a banner with information about the user's trial or subscription status.
 * It fetches the status from the /assinatura/status endpoint and displays an appropriate message.
 */
import React, { useState, useEffect } from "react";
import axios from "axios";

// Styles for the banner
const styles = {
  bannerContainer: {
    width: "100%",
    padding: "12px 16px",
    borderRadius: "4px",
    marginBottom: "16px",
    fontFamily: "Arial, sans-serif",
    position: "relative",
  },
  trial: {
    backgroundColor: "#f0f8ff",
    borderLeft: "4px solid #3498db",
    color: "#333",
  },
  expired: {
    backgroundColor: "#fff5f5",
    borderLeft: "4px solid #e74c3c",
    color: "#333",
  },
  subscribed: {
    backgroundColor: "#f0fff4",
    borderLeft: "4px solid #2ecc71",
    color: "#333",
  },
  title: {
    margin: "0 0 6px 0",
    fontSize: "16px",
    fontWeight: "bold",
  },
  message: {
    margin: "0",
    fontSize: "14px",
    lineHeight: "1.4",
  },
  closeButton: {
    position: "absolute",
    top: "8px",
    right: "8px",
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "16px",
    color: "#666",
  },
  buttonContainer: {
    marginTop: "10px",
  },
  subscribeButton: {
    backgroundColor: "#3498db",
    color: "white",
    border: "none",
    padding: "6px 12px",
    borderRadius: "3px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "bold",
  },
};

const TrialBanner = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    // Fetch subscription status from API
    const fetchStatus = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          setLoading(false);
          return;
        }

        const response = await axios.get("/assinatura/status", {
          headers: { Authorization: `Bearer ${token}` },
        });

        setStatus(response.data);
        setLoading(false);
      } catch (err) {
        console.error("Erro ao buscar status da assinatura:", err);
        setError("Não foi possível verificar o status da sua assinatura.");
        setLoading(false);
      }
    };

    fetchStatus();
  }, []);

  const handleClose = () => {
    setVisible(false);
    // Optionally save to localStorage to avoid showing again for some time
    localStorage.setItem("bannerClosedAt", new Date().toISOString());
  };

  const handleSubscribe = () => {
    // Redirect to subscription page or open subscription modal
    console.log("Redirecionando para página de assinatura...");
    // window.location.href = '/assinatura';
    // OR: openSubscriptionModal();
  };

  if (!visible || loading || !status) return null;

  let bannerStyle,
    title,
    message,
    showButton = false;

  if (status.trialAtivo) {
    bannerStyle = styles.trial;
    title = "Versão de Testes";
    message = `Você está usando o Cíclica em versão de testes. Restam ${status.diasRestantesTrial} dias. Após esse período, será necessário assinar para continuar.`;
    showButton = status.diasRestantesTrial <= 2; // Show button if 2 or less days remain
  } else if (status.assinaturaAtiva) {
    bannerStyle = styles.subscribed;
    title = "Assinatura Ativa";
    message = "Você possui uma assinatura ativa. Aproveite todos os recursos!";
  } else {
    bannerStyle = styles.expired;
    title = "Período de Testes Expirado";
    message =
      "Seu período de testes expirou. Assine agora para continuar usando o app.";
    showButton = true;
  }

  return (
    <div style={{ ...styles.bannerContainer, ...bannerStyle }}>
      <button style={styles.closeButton} onClick={handleClose}>
        ×
      </button>
      <h3 style={styles.title}>{title}</h3>
      <p style={styles.message}>{message}</p>

      {showButton && (
        <div style={styles.buttonContainer}>
          <button style={styles.subscribeButton} onClick={handleSubscribe}>
            Assinar Agora
          </button>
        </div>
      )}
    </div>
  );
};

export default TrialBanner;
