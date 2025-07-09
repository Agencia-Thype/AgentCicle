/**
 * Trial Splash Screen Component
 *
 * This component shows a full-screen splash with information about the trial period
 * when a user logs in for the first time or starts a new trial.
 */
import React, { useState } from "react";

// Styles for the splash screen
const styles = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.7)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1000,
  },
  container: {
    backgroundColor: "white",
    borderRadius: "8px",
    padding: "24px",
    maxWidth: "500px",
    width: "90%",
    textAlign: "center",
    boxShadow: "0 4px 20px rgba(0, 0, 0, 0.2)",
  },
  logo: {
    width: "120px",
    marginBottom: "20px",
  },
  title: {
    fontSize: "24px",
    fontWeight: "bold",
    color: "#e91e63", // Pink color for Cíclica theme
    marginBottom: "16px",
  },
  message: {
    fontSize: "16px",
    lineHeight: "1.6",
    color: "#333",
    marginBottom: "24px",
  },
  highlight: {
    fontWeight: "bold",
    color: "#e91e63",
  },
  button: {
    backgroundColor: "#e91e63",
    color: "white",
    border: "none",
    borderRadius: "4px",
    padding: "12px 24px",
    fontSize: "16px",
    fontWeight: "bold",
    cursor: "pointer",
    transition: "background-color 0.2s",
  },
  featuresList: {
    textAlign: "left",
    marginBottom: "24px",
    paddingLeft: "20px",
  },
  feature: {
    marginBottom: "8px",
    fontSize: "14px",
  },
};

const TrialSplashScreen = ({ onClose, daysRemaining = 7 }) => {
  return (
    <div style={styles.overlay}>
      <div style={styles.container}>
        <img src="/logo-ciclica.png" alt="Cíclica Logo" style={styles.logo} />

        <h1 style={styles.title}>Bem-vinda ao Cíclica!</h1>

        <p style={styles.message}>
          Você está usando o Cíclica em{" "}
          <span style={styles.highlight}>versão de testes</span>. Aproveite
          todos os recursos por{" "}
          <span style={styles.highlight}>{daysRemaining} dias</span>. Após esse
          período, será necessário assinar para continuar.
        </p>

        <div style={styles.featuresList}>
          <p style={styles.feature}>
            ✨ Acompanhe seu ciclo menstrual de forma personalizada
          </p>
          <p style={styles.feature}>
            ✨ Receba treinos adequados para cada fase do seu ciclo
          </p>
          <p style={styles.feature}>
            ✨ Registre sintomas e monitore sua saúde
          </p>
          <p style={styles.feature}>
            ✨ Obtenha insights com nossa Inteligência Artificial
          </p>
        </div>

        <button style={styles.button} onClick={onClose}>
          Começar a Usar
        </button>
      </div>
    </div>
  );
};

export default TrialSplashScreen;
