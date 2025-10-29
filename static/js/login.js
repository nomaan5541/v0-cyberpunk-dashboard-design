document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault()

  const email = document.getElementById("email").value
  const password = document.getElementById("password").value
  const role = document.getElementById("role").value
  const errorDiv = document.getElementById("errorMessage")

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password, role }),
    })

    const data = await response.json()

    if (data.success) {
      window.location.href = "/dashboard"
    } else {
      errorDiv.textContent = data.message || "Login failed"
      errorDiv.style.display = "block"
    }
  } catch (error) {
    errorDiv.textContent = "An error occurred. Please try again."
    errorDiv.style.display = "block"
  }
})
