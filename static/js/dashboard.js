// Navigation
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.preventDefault()
    const page = item.dataset.page

    document.querySelectorAll(".nav-item").forEach((i) => i.classList.remove("active"))
    item.classList.add("active")

    document.querySelectorAll(".page-content").forEach((p) => p.classList.remove("active"))
    document.getElementById(`${page}-page`).classList.add("active")

    document.getElementById("pageTitle").textContent = item.textContent.trim()

    if (page === "dashboard") {
      loadDashboard()
    } else if (page === "students") {
      loadStudents()
    }
  })
})

// Load Dashboard
async function loadDashboard() {
  try {
    const response = await fetch("/api/school-admin/dashboard")
    const data = await response.json()

    document.getElementById("classesActive").textContent = data.total_classes
    document.getElementById("studentsCount").textContent = data.total_students
    document.getElementById("feesCollected").textContent = "₹" + data.fees_collected.toLocaleString()
    document.getElementById("feesDue").textContent = data.fees_due
  } catch (error) {
    console.error("Error loading dashboard:", error)
  }
}

// Load Students
async function loadStudents() {
  try {
    const response = await fetch("/api/students")
    const students = await response.json()

    const tbody = document.getElementById("studentsTable")
    tbody.innerHTML = ""

    students.forEach((student) => {
      const row = document.createElement("tr")
      row.innerHTML = `
                <td>${student.roll_number}</td>
                <td>${student.name}</td>
                <td>${student.class_id}</td>
                <td>${student.phone || "-"}</td>
                <td><span class="status-badge">${student.status}</span></td>
                <td>
                    <button class="btn-small">Edit</button>
                    <button class="btn-small danger">Delete</button>
                </td>
            `
      tbody.appendChild(row)
    })
  } catch (error) {
    console.error("Error loading students:", error)
  }
}

// Initialize
loadDashboard()
