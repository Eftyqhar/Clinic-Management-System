// State Management
let authToken = localStorage.getItem("clinic_token") || null;
let currentUser = null;
let cachedPatients = [];
let cachedDoctors = [];

const API_BASE = "/api/v1";

// DOM References
const authView = document.getElementById("authView");
const dashboardView = document.getElementById("dashboardView");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const btnLogout = document.getElementById("btnLogout");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  if (authToken) {
    loadUserAndInit();
  } else {
    showAuth();
  }

  // Setup tab switches
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchTab(btn.dataset.tab);
    });
  });

  // Login handler
  loginForm.addEventListener("submit", handleLogin);

  // Logout handler
  btnLogout.addEventListener("click", handleLogout);

  // Form submit handlers
  document.getElementById("formPatient").addEventListener("submit", handleCreatePatient);
  document.getElementById("formDoctor").addEventListener("submit", handleCreateDoctor);
  document.getElementById("formAppointment").addEventListener("submit", handleBookAppointment);
  document.getElementById("formConsultation").addEventListener("submit", handleSaveConsultation);
  document.getElementById("formPayInvoice").addEventListener("submit", handlePayInvoice);

  // Patient search input listener
  document.getElementById("patientSearchInput").addEventListener("input", (e) => {
    filterPatients(e.target.value);
  });
});

// Authentication functions
async function handleLogin(e) {
  e.preventDefault();
  loginError.classList.add("hidden");

  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value.trim();

  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Authentication failed");
    }

    const data = await res.json();
    authToken = data.access_token;
    localStorage.setItem("clinic_token", authToken);
    await loadUserAndInit();
  } catch (error) {
    loginError.textContent = error.message;
    loginError.classList.remove("hidden");
  }
}

function handleLogout() {
  localStorage.removeItem("clinic_token");
  authToken = null;
  currentUser = null;
  showAuth();
}

function showAuth() {
  authView.classList.remove("hidden");
  dashboardView.classList.add("hidden");
}

async function loadUserAndInit() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/auth/me`);
    if (!res.ok) throw new Error("Invalid session");
    currentUser = await res.json();

    document.getElementById("navUserName").textContent = currentUser.full_name;
    document.getElementById("navUserRole").textContent = currentUser.role.toUpperCase();

    authView.classList.add("hidden");
    dashboardView.classList.remove("hidden");

    // Load initial dashboard state
    refreshAllData();
  } catch (err) {
    handleLogout();
  }
}

// Fetch helper with Authorization
async function fetchWithAuth(url, options = {}) {
  const headers = options.headers || {};
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  return fetch(url, { ...options, headers });
}

// Navigation & Tab Switching
function switchTab(tabName) {
  // Update button active state
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    if (btn.dataset.tab === tabName) {
      btn.className = "tab-btn px-3 py-2 rounded-lg text-sm font-medium text-indigo-600 bg-indigo-50";
    } else {
      btn.className = "tab-btn px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100";
    }
  });

  // Hide all tab sections
  ["overview", "patients", "doctors", "appointments", "billing"].forEach((t) => {
    const sec = document.getElementById(`tab-${t}`);
    if (sec) sec.classList.add("hidden");
  });

  // Show active tab
  const activeSec = document.getElementById(`tab-${tabName}`);
  if (activeSec) activeSec.classList.remove("hidden");

  // Refresh tab-specific data
  if (tabName === "patients") loadPatients();
  if (tabName === "doctors") loadDoctors();
  if (tabName === "appointments") loadAppointments();
  if (tabName === "billing") loadBilling();
  if (tabName === "overview") refreshAllData();
}

// Modals
function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

// Refresh All Data
async function refreshAllData() {
  await Promise.all([
    loadPatients(),
    loadDoctors(),
    loadAppointments(),
    loadBilling(),
  ]);
  updateOverviewStats();
}

// ---------------- PATIENT FUNCTIONS ----------------
async function loadPatients() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/patients/`);
    if (!res.ok) return;
    cachedPatients = await res.json();
    renderPatients(cachedPatients);
    document.getElementById("statTotalPatients").textContent = cachedPatients.length;
  } catch (err) {
    console.error(err);
  }
}

function renderPatients(patients) {
  const tbody = document.getElementById("patientsTableBody");
  if (!patients.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400">No patients recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = patients.map((p) => `
    <tr class="hover:bg-slate-50/75 transition">
      <td class="py-3 px-4 font-medium text-slate-900">${p.first_name} ${p.last_name}</td>
      <td class="py-3 px-4 text-xs">
        <div>${p.phone}</div>
        <div class="text-slate-400">${p.email || "No email"}</div>
      </td>
      <td class="py-3 px-4">
        <span class="px-2 py-0.5 rounded text-xs font-semibold ${p.blood_group ? 'bg-rose-50 text-rose-600' : 'text-slate-400'}">
          ${p.blood_group || "N/A"}
        </span>
      </td>
      <td class="py-3 px-4 text-xs">${p.gender || "Unspecified"}</td>
      <td class="py-3 px-4 text-xs text-slate-600">${p.allergies || "None"}</td>
      <td class="py-3 px-4 text-right">
        <button onclick="bookApptForPatient('${p.id}')" class="text-xs bg-indigo-50 text-indigo-600 hover:bg-indigo-100 px-2.5 py-1 rounded font-medium">
          Book
        </button>
      </td>
    </tr>
  `).join("");
}

function filterPatients(query) {
  const q = query.toLowerCase();
  const filtered = cachedPatients.filter(
    (p) =>
      p.first_name.toLowerCase().includes(q) ||
      p.last_name.toLowerCase().includes(q) ||
      p.phone.toLowerCase().includes(q)
  );
  renderPatients(filtered);
}

async function handleCreatePatient(e) {
  e.preventDefault();
  const payload = {
    first_name: document.getElementById("pFirstName").value.trim(),
    last_name: document.getElementById("pLastName").value.trim(),
    phone: document.getElementById("pPhone").value.trim(),
    email: document.getElementById("pEmail").value.trim() || null,
    blood_group: document.getElementById("pBloodGroup").value || null,
    gender: document.getElementById("pGender").value || null,
    date_of_birth: document.getElementById("pDob").value || null,
    allergies: document.getElementById("pAllergies").value.trim() || null,
  };

  const res = await fetchWithAuth(`${API_BASE}/patients/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    document.getElementById("formPatient").reset();
    closeModal("modalPatient");
    await loadPatients();
  } else {
    const err = await res.json();
    alert(`Error: ${err.detail || "Failed to create patient"}`);
  }
}

// ---------------- DOCTOR FUNCTIONS ----------------
async function loadDoctors() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/doctors/`);
    if (!res.ok) return;
    cachedDoctors = await res.json();
    renderDoctors(cachedDoctors);
    document.getElementById("statTotalDoctors").textContent = cachedDoctors.length;
  } catch (err) {
    console.error(err);
  }
}

function renderDoctors(doctors) {
  const grid = document.getElementById("doctorsGrid");
  if (!doctors.length) {
    grid.innerHTML = `<div class="col-span-3 text-center py-8 text-slate-400">No doctor profiles found. Add one to get started.</div>`;
    return;
  }

  grid.innerHTML = doctors.map((doc) => `
    <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow transition flex flex-col justify-between">
      <div>
        <div class="flex items-center space-x-3 mb-3">
          <div class="w-12 h-12 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-lg">
            ${doc.user ? doc.user.full_name[0] : "D"}
          </div>
          <div>
            <h3 class="font-bold text-slate-800 text-base">${doc.user ? doc.user.full_name : "Doctor"}</h3>
            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600">
              ${doc.specialization}
            </span>
          </div>
        </div>
        <p class="text-xs text-slate-500 mb-4">${doc.bio || "No profile biography provided."}</p>
      </div>

      <div class="pt-4 border-t border-slate-100 flex items-center justify-between">
        <div>
          <span class="text-xs text-slate-400 block leading-tight">Consultation</span>
          <span class="text-sm font-bold text-emerald-600">$${doc.consultation_fee.toFixed(2)}</span>
        </div>
        <button onclick="bookApptWithDoctor('${doc.id}')" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg font-medium">
          Schedule Slot
        </button>
      </div>
    </div>
  `).join("");
}

async function handleCreateDoctor(e) {
  e.preventDefault();
  const fullName = document.getElementById("dFullName").value.trim();
  const email = document.getElementById("dEmail").value.trim();
  const password = document.getElementById("dPassword").value.trim();
  const specialization = document.getElementById("dSpecialization").value.trim();
  const fee = parseFloat(document.getElementById("dFee").value);
  const phone = document.getElementById("dPhone").value.trim() || null;

  // 1. Create User account first
  const userRes = await fetchWithAuth(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
      role: "doctor",
    }),
  });

  if (!userRes.ok) {
    const err = await userRes.json();
    alert(`Failed to create account: ${err.detail || "Error"}`);
    return;
  }

  const user = await userRes.json();

  // 2. Create Doctor profile linked to user
  const docRes = await fetchWithAuth(`${API_BASE}/doctors/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: user.id,
      specialization,
      consultation_fee: fee,
      phone,
    }),
  });

  if (docRes.ok) {
    document.getElementById("formDoctor").reset();
    closeModal("modalDoctor");
    await loadDoctors();
  } else {
    const err = await docRes.json();
    alert(`Failed to create doctor profile: ${err.detail || "Error"}`);
  }
}

// ---------------- APPOINTMENTS FUNCTIONS ----------------
let cachedAppointments = [];

async function loadAppointments() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/appointments/`);
    if (!res.ok) return;
    cachedAppointments = await res.json();
    renderAppointments(cachedAppointments);
    document.getElementById("statTotalAppointments").textContent = cachedAppointments.length;
  } catch (err) {
    console.error(err);
  }
}

function renderAppointments(appts) {
  const tbody = document.getElementById("appointmentsTableBody");
  const overviewTbody = document.getElementById("overviewAppointmentsBody");

  if (!appts.length) {
    const emptyRow = `<tr><td colspan="6" class="text-center py-6 text-slate-400">No scheduled appointments found.</td></tr>`;
    tbody.innerHTML = emptyRow;
    overviewTbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-slate-400">No recent bookings.</td></tr>`;
    return;
  }

  // Populate Main Table
  tbody.innerHTML = appts.map((a) => {
    const patientName = a.patient ? `${a.patient.first_name} ${a.patient.last_name}` : "Patient";
    const doctorName = a.doctor && a.doctor.user ? a.doctor.user.full_name : "Specialist";
    return `
      <tr class="hover:bg-slate-50/75 transition">
        <td class="py-3 px-4 font-medium text-slate-900">${patientName}</td>
        <td class="py-3 px-4 text-xs text-slate-600">${doctorName}</td>
        <td class="py-3 px-4 text-xs">${a.appointment_date}</td>
        <td class="py-3 px-4 text-xs">${a.start_time.slice(0, 5)} - ${a.end_time.slice(0, 5)}</td>
        <td class="py-3 px-4">${renderStatusBadge(a.status)}</td>
        <td class="py-3 px-4 text-right space-x-1">
          ${a.status !== "completed" ? `
            <button onclick="openConsultationModal('${a.id}', '${patientName}')" class="text-xs bg-emerald-50 text-emerald-700 hover:bg-emerald-100 px-2.5 py-1 rounded font-medium">
              Consult
            </button>
          ` : `
            <span class="text-xs text-emerald-600 font-semibold"><i class="fa-solid fa-check mr-1"></i>Completed</span>
          `}
        </td>
      </tr>
    `;
  }).join("");

  // Populate Overview Table (top 5)
  overviewTbody.innerHTML = appts.slice(0, 5).map((a) => {
    const patientName = a.patient ? `${a.patient.first_name} ${a.patient.last_name}` : "Patient";
    const doctorName = a.doctor && a.doctor.user ? a.doctor.user.full_name : "Specialist";
    return `
      <tr class="hover:bg-slate-50/75">
        <td class="py-2.5 px-3 font-medium text-slate-900">${patientName}</td>
        <td class="py-2.5 px-3 text-xs text-slate-600">${doctorName}</td>
        <td class="py-2.5 px-3 text-xs">${a.appointment_date} (${a.start_time.slice(0, 5)})</td>
        <td class="py-2.5 px-3">${renderStatusBadge(a.status)}</td>
      </tr>
    `;
  }).join("");
}

function renderStatusBadge(status) {
  const colors = {
    scheduled: "bg-blue-50 text-blue-700 border-blue-200",
    confirmed: "bg-indigo-50 text-indigo-700 border-indigo-200",
    completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    cancelled: "bg-rose-50 text-rose-700 border-rose-200",
  };
  return `<span class="px-2 py-0.5 rounded text-xs border font-medium uppercase ${colors[status] || 'bg-slate-100 text-slate-700'}">${status}</span>`;
}

function openAppointmentModal() {
  // Populate patient and doctor dropdowns
  const pSelect = document.getElementById("apptPatientSelect");
  const dSelect = document.getElementById("apptDoctorSelect");

  pSelect.innerHTML = `<option value="">Choose patient...</option>` +
    cachedPatients.map((p) => `<option value="${p.id}">${p.first_name} ${p.last_name} (${p.phone})</option>`).join("");

  dSelect.innerHTML = `<option value="">Choose doctor...</option>` +
    cachedDoctors.map((d) => `<option value="${d.id}">${d.user ? d.user.full_name : "Doctor"} - ${d.specialization} ($${d.consultation_fee})</option>`).join("");

  // Set default date to today
  document.getElementById("apptDate").value = new Date().toISOString().split("T")[0];
  document.getElementById("apptError").classList.add("hidden");

  openModal("modalAppointment");
}

function bookApptForPatient(patientId) {
  openAppointmentModal();
  document.getElementById("apptPatientSelect").value = patientId;
}

function bookApptWithDoctor(doctorId) {
  openAppointmentModal();
  document.getElementById("apptDoctorSelect").value = doctorId;
}

async function handleBookAppointment(e) {
  e.preventDefault();
  const errBox = document.getElementById("apptError");
  errBox.classList.add("hidden");

  const payload = {
    patient_id: document.getElementById("apptPatientSelect").value,
    doctor_id: document.getElementById("apptDoctorSelect").value,
    appointment_date: document.getElementById("apptDate").value,
    start_time: document.getElementById("apptStart").value + ":00",
    end_time: document.getElementById("apptEnd").value + ":00",
    reason: document.getElementById("apptReason").value.trim() || null,
  };

  const res = await fetchWithAuth(`${API_BASE}/appointments/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    closeModal("modalAppointment");
    await refreshAllData();
  } else {
    const err = await res.json();
    errBox.textContent = err.detail || "Failed to book appointment.";
    errBox.classList.remove("hidden");
  }
}

// ---------------- CONSULTATION & PRESCRIPTION ----------------
let rxCount = 0;

function openConsultationModal(appointmentId, patientName) {
  document.getElementById("consAppointmentId").value = appointmentId;
  document.getElementById("consHeaderSub").textContent = `Patient: ${patientName}`;
  document.getElementById("rxContainer").innerHTML = "";
  document.getElementById("formConsultation").reset();
  rxCount = 0;
  addRxRow(); // Add one initial empty row
  openModal("modalConsultation");
}

function addRxRow() {
  rxCount++;
  const div = document.createElement("div");
  div.className = "grid grid-cols-4 gap-2 bg-white p-2.5 rounded-lg border border-slate-300 text-xs items-center shadow-sm";
  div.id = `rxRow_${rxCount}`;
  div.innerHTML = `
    <input type="text" placeholder="Medication (e.g. Paracetamol)" required class="rx-name border border-slate-300 bg-white text-slate-900 font-medium rounded px-2.5 py-1.5 outline-none col-span-1 focus:ring-1 focus:ring-indigo-500">
    <input type="text" placeholder="Dosage (500mg)" required class="rx-dose border border-slate-300 bg-white text-slate-900 font-medium rounded px-2.5 py-1.5 outline-none focus:ring-1 focus:ring-indigo-500">
    <input type="text" placeholder="Frequency (Twice daily)" required class="rx-freq border border-slate-300 bg-white text-slate-900 font-medium rounded px-2.5 py-1.5 outline-none focus:ring-1 focus:ring-indigo-500">
    <div class="flex items-center space-x-1">
      <input type="text" placeholder="Duration (5 days)" required class="rx-dur border border-slate-300 bg-white text-slate-900 font-medium rounded px-2.5 py-1.5 outline-none w-full focus:ring-1 focus:ring-indigo-500">
      <button type="button" onclick="this.closest('#rxRow_${rxCount}').remove()" class="text-rose-500 hover:text-rose-700 p-1.5 hover:bg-rose-50 rounded"><i class="fa-solid fa-trash-can"></i></button>
    </div>
  `;
  document.getElementById("rxContainer").appendChild(div);
}

async function handleSaveConsultation(e) {
  e.preventDefault();
  const appointmentId = document.getElementById("consAppointmentId").value;
  const vitals = document.getElementById("consVitals").value.trim() || null;
  const symptoms = document.getElementById("consSymptoms").value.trim() || null;
  const diagnosis = document.getElementById("consDiagnosis").value.trim();
  const treatment = document.getElementById("consTreatment").value.trim() || null;

  // Gather prescriptions
  const prescriptions = [];
  document.querySelectorAll("#rxContainer > div").forEach((row) => {
    const name = row.querySelector(".rx-name")?.value.trim();
    const dose = row.querySelector(".rx-dose")?.value.trim();
    const freq = row.querySelector(".rx-freq")?.value.trim();
    const dur = row.querySelector(".rx-dur")?.value.trim();
    if (name && dose && freq && dur) {
      prescriptions.push({
        medication_name: name,
        dosage: dose,
        frequency: freq,
        duration: dur,
      });
    }
  });

  const payload = {
    appointment_id: appointmentId,
    diagnosis,
    symptoms,
    vitals,
    treatment_plan: treatment,
    prescriptions,
  };

  const res = await fetchWithAuth(`${API_BASE}/consultations/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    closeModal("modalConsultation");
    await refreshAllData();
  } else {
    const err = await res.json();
    alert(`Failed to save consultation: ${err.detail || "Error"}`);
  }
}

// ---------------- BILLING FUNCTIONS ----------------
let cachedInvoices = [];

async function loadBilling() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/billing/`);
    if (!res.ok) return;
    cachedInvoices = await res.json();
    renderBilling(cachedInvoices);
  } catch (err) {
    console.error(err);
  }
}

function renderBilling(invoices) {
  const tbody = document.getElementById("billingTableBody");
  if (!invoices.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400">No invoices recorded.</td></tr>`;
    return;
  }

  let totalRev = 0;
  tbody.innerHTML = invoices.map((inv) => {
    totalRev += inv.paid_amount;
    const isPaid = inv.status === "paid";
    return `
      <tr class="hover:bg-slate-50/75 transition">
        <td class="py-3 px-4 font-mono text-xs text-slate-500">${inv.id.slice(0, 8)}...</td>
        <td class="py-3 px-4 font-semibold text-slate-900">$${inv.total_amount.toFixed(2)}</td>
        <td class="py-3 px-4 text-emerald-600 font-semibold">$${inv.paid_amount.toFixed(2)}</td>
        <td class="py-3 px-4 text-xs text-slate-600">${inv.payment_method || "Pending"}</td>
        <td class="py-3 px-4">
          <span class="px-2 py-0.5 rounded text-xs font-semibold ${isPaid ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}">
            ${inv.status.toUpperCase()}
          </span>
        </td>
        <td class="py-3 px-4 text-right">
          ${!isPaid ? `
            <button onclick="openPayModal('${inv.id}', ${inv.total_amount - inv.paid_amount})" class="text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 px-3 py-1 rounded font-medium">
              Collect
            </button>
          ` : `
            <span class="text-xs text-slate-400 font-medium">Settled</span>
          `}
        </td>
      </tr>
    `;
  }).join("");

  document.getElementById("statTotalRevenue").textContent = `$${totalRev.toFixed(2)}`;
}

function openPayModal(invoiceId, balance) {
  document.getElementById("payInvoiceId").value = invoiceId;
  document.getElementById("payInvoiceTotal").textContent = `$${balance.toFixed(2)}`;
  document.getElementById("payAmount").value = balance;
  openModal("modalPayInvoice");
}

async function handlePayInvoice(e) {
  e.preventDefault();
  const invoiceId = document.getElementById("payInvoiceId").value;
  const paidAmount = parseFloat(document.getElementById("payAmount").value);
  const paymentMethod = document.getElementById("payMethod").value;

  const res = await fetchWithAuth(`${API_BASE}/billing/${invoiceId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paid_amount: paidAmount,
      payment_method: paymentMethod,
    }),
  });

  if (res.ok) {
    closeModal("modalPayInvoice");
    await refreshAllData();
  } else {
    const err = await res.json();
    alert(`Payment failed: ${err.detail || "Error"}`);
  }
}

function updateOverviewStats() {
  document.getElementById("statTotalPatients").textContent = cachedPatients.length;
  document.getElementById("statTotalDoctors").textContent = cachedDoctors.length;
  document.getElementById("statTotalAppointments").textContent = cachedAppointments.length;
  const totalRev = cachedInvoices.reduce((acc, curr) => acc + (curr.paid_amount || 0), 0);
  document.getElementById("statTotalRevenue").textContent = `$${totalRev.toFixed(2)}`;
}
