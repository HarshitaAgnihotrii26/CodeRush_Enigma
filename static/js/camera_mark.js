// camera_mark.js
const startMarkBtn = document.getElementById("startMarkBtn");
const stopMarkBtn = document.getElementById("stopMarkBtn");
const markVideo = document.getElementById("markVideo");
const markStatus = document.getElementById("markStatus");
const recognizedList = document.getElementById("recognizedList");

let markStream = null;
let markInterval = null;
let recognizedIds = new Set();

startMarkBtn.addEventListener("click", async () => {
  startMarkBtn.disabled = true;
  stopMarkBtn.disabled = false;
  try {
    markStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
    markVideo.srcObject = markStream;
    await markVideo.play();
    markStatus.innerText = "Scanning...";
    markInterval = setInterval(captureAndRecognize, 800);
  } catch (err) {
    alert("Camera error: " + err.message);
    startMarkBtn.disabled = false;
    stopMarkBtn.disabled = true;
  }
});

stopMarkBtn.addEventListener("click", () => {
  if (markInterval) clearInterval(markInterval);
  if (markStream) markStream.getTracks().forEach(t => t.stop());
  startMarkBtn.disabled = false;
  stopMarkBtn.disabled = true;
  markStatus.innerText = "Stopped";
});

async function captureAndRecognize() {
  const canvas = document.createElement("canvas");
  canvas.width = markVideo.videoWidth || 640;
  canvas.height = markVideo.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(markVideo, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise(r => canvas.toBlob(r, "image/jpeg", 0.85));
  const fd = new FormData();
  fd.append("image", blob, "snap.jpg");
  try {
    const res = await fetch("/recognize_face", { method: "POST", body: fd });
    const j = await res.json();
    if (j.recognized) {
      markStatus.innerText = `Recognized: ${j.name} (conf ${Math.round(j.confidence*100)}%)`;
      if (!recognizedIds.has(j.student_id)) {
        recognizedIds.add(j.student_id);
        const li = document.createElement("li");
        li.className = "list-group-item";
        li.innerText = `${j.name} — ${new Date().toLocaleTimeString()}`;
        recognizedList.prepend(li);
      }
    } else {
      if (j.error) markStatus.innerText = `Not recognized: ${j.error}`;
      else markStatus.innerText = `Not recognized`;
    }
  } catch (err) {
    console.error(err);
  }
}

// =====================================================
// PHOTO UPLOAD FUNCTIONALITY
// =====================================================
const photoDropZone = document.getElementById("photoDropZone");
const photoInput = document.getElementById("photoInput");
const photoPreview = document.getElementById("photoPreview");
const recognizePhotoBtn = document.getElementById("recognizePhotoBtn");
const photoResult = document.getElementById("photoResult");

let selectedPhotoFile = null;

photoDropZone.addEventListener("click", () => photoInput.click());

photoDropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  photoDropZone.classList.add("dragover");
});

photoDropZone.addEventListener("dragleave", () => {
  photoDropZone.classList.remove("dragover");
});

photoDropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  photoDropZone.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (files.length > 0) handlePhotoFile(files[0]);
});

photoInput.addEventListener("change", () => {
  if (photoInput.files.length > 0) handlePhotoFile(photoInput.files[0]);
});

function handlePhotoFile(file) {
  if (!file.type.startsWith("image/")) {
    alert("Please select an image file");
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    alert("File size must be less than 5MB");
    return;
  }
  selectedPhotoFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    photoPreview.src = e.target.result;
    photoPreview.classList.remove("d-none");
  };
  reader.readAsDataURL(file);
  recognizePhotoBtn.disabled = false;
  photoResult.innerHTML = `<p class="text-success">Photo selected: ${file.name}</p>`;
}

recognizePhotoBtn.addEventListener("click", async () => {
  if (!selectedPhotoFile) return;
  
  recognizePhotoBtn.disabled = true;
  photoResult.innerHTML = '<p class="text-info">Processing...</p>';
  
  const fd = new FormData();
  fd.append("image", selectedPhotoFile);
  
  try {
    const res = await fetch("/recognize_face", { method: "POST", body: fd });
    const j = await res.json();
    
    if (j.recognized) {
      photoResult.innerHTML = `
        <div class="alert alert-success">
          <strong>Attendance Marked!</strong><br>
          Name: ${j.name}<br>
          Student ID: ${j.student_id}<br>
          Confidence: ${Math.round(j.confidence * 100)}%
          ${j.note ? '<br><small>' + j.note + '</small>' : ''}
        </div>
      `;
    } else {
      photoResult.innerHTML = `
        <div class="alert alert-warning">
          <strong>Not Recognized</strong><br>
          ${j.error || 'Face not found or not matched'}
        </div>
      `;
    }
  } catch (err) {
    photoResult.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
  }
  
  recognizePhotoBtn.disabled = false;
});

// =====================================================
// DOCUMENT UPLOAD FUNCTIONALITY
// =====================================================
const docDropZone = document.getElementById("docDropZone");
const docInput = document.getElementById("docInput");
const docFileList = document.getElementById("docFileList");
const uploadDocBtn = document.getElementById("uploadDocBtn");
const docUploadStatus = document.getElementById("docUploadStatus");
const uploadedDocsList = document.getElementById("uploadedDocsList");
const docStudentId = document.getElementById("docStudentId");
const docDescription = document.getElementById("docDescription");

let selectedDocFile = null;

docDropZone.addEventListener("click", () => docInput.click());

docDropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  docDropZone.classList.add("dragover");
});

docDropZone.addEventListener("dragleave", () => {
  docDropZone.classList.remove("dragover");
});

docDropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  docDropZone.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (files.length > 0) handleDocFile(files[0]);
});

docInput.addEventListener("change", () => {
  if (docInput.files.length > 0) handleDocFile(docInput.files[0]);
});

function handleDocFile(file) {
  const allowedTypes = ['application/pdf', 'application/msword', 
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg', 'image/png'];
  
  if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|doc|docx|jpg|jpeg|png)$/i)) {
    alert("Allowed formats: PDF, DOC, DOCX, JPG, PNG");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    alert("File size must be less than 10MB");
    return;
  }
  
  selectedDocFile = file;
  docFileList.innerHTML = `
    <div class="file-item">
      <span class="file-name">${file.name}</span>
      <button class="btn btn-sm btn-outline-danger" onclick="clearDocFile()">×</button>
    </div>
  `;
  uploadDocBtn.disabled = false;
}

function clearDocFile() {
  selectedDocFile = null;
  docFileList.innerHTML = '';
  docInput.value = '';
  uploadDocBtn.disabled = true;
}

// Make clearDocFile accessible globally
window.clearDocFile = clearDocFile;

uploadDocBtn.addEventListener("click", async () => {
  if (!selectedDocFile) return;
  
  uploadDocBtn.disabled = true;
  docUploadStatus.innerHTML = '<span class="text-info">Uploading...</span>';
  
  const fd = new FormData();
  fd.append("document", selectedDocFile);
  fd.append("student_id", docStudentId.value || "");
  fd.append("description", docDescription.value || "");
  
  try {
    const res = await fetch("/upload_document", { method: "POST", body: fd });
    const j = await res.json();
    
    if (j.success) {
      docUploadStatus.innerHTML = '<span class="text-success">Document uploaded successfully!</span>';
      clearDocFile();
      docStudentId.value = '';
      docDescription.value = '';
      loadUploadedDocs();
    } else {
      docUploadStatus.innerHTML = `<span class="text-danger">Error: ${j.error}</span>`;
    }
  } catch (err) {
    docUploadStatus.innerHTML = `<span class="text-danger">Error: ${err.message}</span>`;
  }
  
  uploadDocBtn.disabled = false;
});

async function loadUploadedDocs() {
  try {
    const res = await fetch("/list_documents");
    const docs = await res.json();
    
    if (docs.length === 0) {
      uploadedDocsList.innerHTML = '<p class="text-muted">No documents uploaded yet</p>';
      return;
    }
    
    let html = '<div class="list-group">';
    docs.forEach(doc => {
      html += `
        <div class="list-group-item d-flex justify-content-between align-items-center">
          <div>
            <strong>${doc.filename}</strong>
            ${doc.student_id ? '<br><small>Student ID: ' + doc.student_id + '</small>' : ''}
            ${doc.description ? '<br><small class="text-muted">' + doc.description + '</small>' : ''}
            <br><small class="text-muted">${doc.uploaded_at}</small>
          </div>
          <a href="/download_document/${doc.id}" class="btn btn-sm btn-outline-primary">Download</a>
        </div>
      `;
    });
    html += '</div>';
    uploadedDocsList.innerHTML = html;
  } catch (err) {
    console.error(err);
  }
}

// Load documents on page load
document.addEventListener("DOMContentLoaded", loadUploadedDocs);