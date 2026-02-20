import { useState, useEffect, useRef } from "react";

/* ═══════════════════════════════════════════════════════════════
   GCLBA Application Portal — Visual Redesign v2
   
   Civic green primary + civic blue secondary highlights.
   Broken-up section layout instead of monolithic white card.
   Warm, authoritative, trustworthy.
   ═══════════════════════════════════════════════════════════════ */

const STEPS = [
  { id: 1, label: "Your Information", shortLabel: "Info", icon: "person" },
  { id: 2, label: "Property Details", shortLabel: "Property", icon: "home" },
  { id: 3, label: "Your Offer", shortLabel: "Offer", icon: "dollar" },
  { id: 4, label: "Eligibility", shortLabel: "Eligibility", icon: "shield" },
  { id: 5, label: "Documents", shortLabel: "Docs", icon: "file" },
  { id: 6, label: "Acknowledgments", shortLabel: "Review", icon: "check" },
];

const PROGRAMS = [
  { value: "featured", label: "Featured Homes", desc: "Move-in ready properties shown at weekly open houses" },
  { value: "rehab", label: "Ready for Rehab", desc: "Properties requiring renovation with a 12-month compliance plan" },
  { value: "vip", label: "VIP Spotlight", desc: "Premium properties with additional requirements" },
  { value: "demo", label: "Demolition", desc: "Structures approved for demolition with environmental compliance" },
];

const PURCHASE_TYPES = [
  { value: "cash", label: "Cash Purchase", docs: ["Photo ID", "Proof of Funds"] },
  { value: "conventional", label: "Conventional Mortgage", docs: ["Photo ID", "Pre-approval Letter"] },
  { value: "land_contract", label: "Land Contract", docs: ["Photo ID", "Pay Stubs (2 months)", "Bank Statements (2 months)"] },
];

/* ─── Color tokens ─── */
const C = {
  green: { 
    50: "#f0f7f1", 100: "#dceede", 200: "#b8ddb9", 600: "#2e7d32", 700: "#256929", 800: "#1b5e20", 900: "#0d3311" 
  },
  blue: { 
    50: "#eff4f8", 100: "#dae6f0", 200: "#b4cde0", 500: "#3d7ea6", 600: "#2d6a8a", 700: "#1e5673", 800: "#184862" 
  },
};

/* ─── Icons ─── */
function Icon({ name, size = 20, className = "" }) {
  const paths = {
    person: <><circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" strokeWidth="1.75"/><path d="M4 21v-1a6 6 0 0 1 12 0v1" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></>,
    home: <path d="M3 12l9-8 9 8M5 12v7a1 1 0 001 1h3v-5h6v5h3a1 1 0 001-1v-7" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>,
    dollar: <><line x1="12" y1="2" x2="12" y2="22" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/><path d="M17 5H9.5a3.5 3.5 0 100 7h5a3.5 3.5 0 110 7H6" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></>,
    shield: <path d="M12 3l7 4v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V7l7-4z" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/>,
    file: <><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></>,
    check: <><path d="M22 11.08V12a10 10 0 11-5.93-9.14" fill="none" stroke="currentColor" strokeWidth="1.75"/><path d="M22 4L12 14.01l-3-3" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></>,
    chevronRight: <path d="M9 18l6-6-6-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>,
    chevronLeft: <path d="M15 18l-6-6 6-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>,
    upload: <><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><polyline points="17,8 12,3 7,8" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></>,
    bookmark: <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/>,
    alertCircle: <><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.75"/><line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/><circle cx="12" cy="16" r="1" fill="currentColor"/></>,
    checkCircle: <><path d="M22 11.08V12a10 10 0 11-5.93-9.14" fill="none" stroke="currentColor" strokeWidth="1.75"/><path d="M22 4L12 14.01l-3-3" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></>,
    xCircle: <><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.75"/><path d="M15 9l-6 6M9 9l6 6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></>,
    lock: <><rect x="3" y="11" width="18" height="11" rx="2" ry="2" fill="none" stroke="currentColor" strokeWidth="1.75"/><path d="M7 11V7a5 5 0 0110 0v4" fill="none" stroke="currentColor" strokeWidth="1.75"/></>,
    info: <><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.75"/><line x1="12" y1="16" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/><circle cx="12" cy="8" r="1" fill="currentColor"/></>,
    externalLink: <><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><polyline points="15,3 21,3 21,9" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><line x1="10" y1="14" x2="21" y2="3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      {paths[name]}
    </svg>
  );
}

/* ─── Form field ─── */
function FormField({ label, required, type = "text", placeholder, hint, children, className = "" }) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <label className="block text-sm font-medium" style={{ fontFamily: "var(--f-body)", color: "var(--c-text)" }}>
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children || (
        <input
          type={type}
          placeholder={placeholder}
          className="w-full px-3.5 py-2.5 rounded-lg text-sm transition-all duration-150"
          style={{
            fontFamily: "var(--f-body)",
            color: "var(--c-text)",
            background: "var(--c-input-bg)",
            border: "1.5px solid var(--c-input-border)",
            outline: "none",
          }}
          onFocus={(e) => { e.target.style.borderColor = C.green[600]; e.target.style.boxShadow = `0 0 0 3px ${C.green[50]}`; }}
          onBlur={(e) => { e.target.style.borderColor = "var(--c-input-border)"; e.target.style.boxShadow = "none"; }}
        />
      )}
      {hint && <p className="text-xs" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>{hint}</p>}
    </div>
  );
}

/* ─── Radio card ─── */
function RadioCard({ selected, label, desc, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-xl transition-all duration-200"
      style={{
        border: selected ? `2px solid ${C.green[600]}` : "2px solid var(--c-section-border)",
        background: selected ? C.green[50] : "var(--c-section-bg)",
      }}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-colors"
          style={{ border: `2px solid ${selected ? C.green[600] : "#c4beb6"}` }}>
          {selected && <div className="w-2.5 h-2.5 rounded-full" style={{ background: C.green[600] }} />}
        </div>
        <div>
          <p className="text-sm font-semibold" style={{ fontFamily: "var(--f-body)", color: "var(--c-text)" }}>{label}</p>
          {desc && <p className="text-xs mt-0.5 leading-relaxed" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>{desc}</p>}
        </div>
      </div>
    </button>
  );
}

/* ─── Upload zone ─── */
function UploadZone({ label }) {
  const [file, setFile] = useState(null);
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium" style={{ fontFamily: "var(--f-body)", color: "var(--c-text)" }}>
        {label} <span className="text-red-500">*</span>
      </label>
      {file ? (
        <div className="flex items-center gap-3 p-3 rounded-lg" style={{ background: C.green[50], border: `1px solid ${C.green[200]}` }}>
          <Icon name="checkCircle" size={18} className="flex-shrink-0" style={{ color: C.green[600] }} />
          <span className="text-sm truncate flex-1" style={{ fontFamily: "var(--f-body)", color: C.green[800] }}>{file}</span>
          <button onClick={() => setFile(null)} className="opacity-50 hover:opacity-80"><Icon name="xCircle" size={16} /></button>
        </div>
      ) : (
        <button
          onClick={() => setFile("document_upload.pdf")}
          className="w-full flex flex-col items-center gap-2 p-6 rounded-xl transition-all duration-200 group cursor-pointer"
          style={{ border: `2px dashed var(--c-input-border)`, background: "transparent" }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = C.blue[500]; e.currentTarget.style.background = C.blue[50]; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--c-input-border)"; e.currentTarget.style.background = "transparent"; }}
        >
          <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: C.blue[50] }}>
            <Icon name="upload" size={20} style={{ color: C.blue[600] }} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium" style={{ fontFamily: "var(--f-body)", color: C.blue[700] }}>
              Click to upload or drag and drop
            </p>
            <p className="text-xs mt-0.5" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
              PDF, JPG, or PNG up to 10MB
            </p>
          </div>
        </button>
      )}
    </div>
  );
}

/* ─── Section card: each logical group gets its own card ─── */
function SectionCard({ children, className = "" }) {
  return (
    <div className={`rounded-2xl p-5 sm:p-6 ${className}`} style={{
      background: "var(--c-section-bg)",
      border: "1px solid var(--c-section-border)",
    }}>
      {children}
    </div>
  );
}

function SectionLabel({ children, blue }) {
  const color = blue ? C.blue[600] : C.green[700];
  return (
    <div className="flex items-center gap-3 mb-5">
      <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ fontFamily: "var(--f-mono)", color }}>{children}</p>
      <div className="flex-1 h-px" style={{ background: blue ? C.blue[200] : "var(--c-section-border)" }} />
    </div>
  );
}

/* ─── Step header ─── */
function StepHeader({ number, title, subtitle }) {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-2">
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-xs font-bold"
          style={{ fontFamily: "var(--f-mono)", background: C.green[700] }}>{number}</span>
        <h2 className="text-2xl sm:text-[28px] font-bold" style={{ fontFamily: "var(--f-title)", color: "var(--c-text)" }}>{title}</h2>
      </div>
      <p className="text-sm leading-relaxed pl-11" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>{subtitle}</p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   STEP CONTENT
   ═══════════════════════════════════════════════════════════════ */

function Step1() {
  return (
    <div className="space-y-6">
      <StepHeader number={1} title="Your Information" subtitle="We will use this to contact you about your application status." />
      
      <SectionCard>
        <SectionLabel>Personal Details</SectionLabel>
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <FormField label="First Name" required placeholder="John" />
            <FormField label="Last Name" required placeholder="Smith" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <FormField label="Email Address" required type="email" placeholder="john.smith@email.com" />
            <FormField label="Phone Number" required type="tel" placeholder="(810) 555-0123" />
          </div>
          <FormField label="Preferred Contact Method" required>
            <div className="flex gap-3 flex-wrap">
              {["Email", "Phone", "Text"].map((m, i) => (
                <button key={m} className="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150"
                  style={{
                    fontFamily: "var(--f-body)",
                    border: i === 0 ? `2px solid ${C.green[600]}` : "2px solid var(--c-input-border)",
                    background: i === 0 ? C.green[50] : "transparent",
                    color: i === 0 ? C.green[700] : "var(--c-muted)",
                  }}>{m}</button>
              ))}
            </div>
          </FormField>
        </div>
      </SectionCard>

      <SectionCard>
        <SectionLabel blue>Current Mailing Address</SectionLabel>
        <div className="space-y-5">
          <FormField label="Street Address" required placeholder="123 Main Street" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <FormField label="City" required placeholder="Flint" className="col-span-2 sm:col-span-2" />
            <FormField label="State" required placeholder="MI" />
            <FormField label="ZIP Code" required placeholder="48502" />
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

function Step2() {
  const [program, setProgram] = useState("featured");
  return (
    <div className="space-y-6">
      <StepHeader number={2} title="Property Details" subtitle="Identify the property and the program it falls under." />

      <SectionCard>
        <SectionLabel>Property Identification</SectionLabel>
        <div className="space-y-5">
          <FormField label="Property Address" required placeholder="307 Mason St, Flint, MI 48503" hint="Enter the full street address of the GCLBA property" />
          <FormField label="Parcel ID Number" required placeholder="41-06-538-004" hint="Found on the property listing or the Flint Property Portal" />
        </div>
      </SectionCard>

      <SectionCard>
        <SectionLabel blue>Program Type</SectionLabel>
        <p className="text-sm mb-4 -mt-2" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
          Select the program this property is listed under.{" "}
          <a href="https://www.thelandbank.org/policies.asp" target="_blank" rel="noopener" className="underline underline-offset-2" style={{ color: C.blue[600] }}>
            View program policies
            <Icon name="externalLink" size={11} className="inline ml-0.5 -mt-0.5" />
          </a>
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {PROGRAMS.map((p) => (
            <RadioCard key={p.value} selected={program === p.value} label={p.label} desc={p.desc} onClick={() => setProgram(p.value)} />
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function Step3() {
  const [purchaseType, setPurchaseType] = useState("cash");
  return (
    <div className="space-y-6">
      <StepHeader number={3} title="Your Offer" subtitle="Provide your offer details and financing plan." />

      <SectionCard>
        <SectionLabel>Offer Details</SectionLabel>
        <div className="space-y-5">
          <FormField label="Offer Amount" required type="text" placeholder="$5,000.00" hint="All properties are sold AS IS. Offers are reviewed on a case-by-case basis." />
          <FormField label="Intended Use" required>
            <textarea
              rows={3}
              placeholder="Describe your plans for the property (e.g., primary residence, rental, renovation for resale)"
              className="w-full px-3.5 py-2.5 rounded-lg text-sm resize-none transition-all duration-150"
              style={{
                fontFamily: "var(--f-body)", color: "var(--c-text)",
                background: "var(--c-input-bg)", border: "1.5px solid var(--c-input-border)", outline: "none",
              }}
              onFocus={(e) => { e.target.style.borderColor = C.green[600]; e.target.style.boxShadow = `0 0 0 3px ${C.green[50]}`; }}
              onBlur={(e) => { e.target.style.borderColor = "var(--c-input-border)"; e.target.style.boxShadow = "none"; }}
            />
          </FormField>
        </div>
      </SectionCard>

      <SectionCard>
        <SectionLabel blue>Purchase Type</SectionLabel>
        <div className="space-y-3">
          {PURCHASE_TYPES.map((t) => (
            <RadioCard key={t.value} selected={purchaseType === t.value} label={t.label} desc={`Required documents: ${t.docs.join(", ")}`} onClick={() => setPurchaseType(t.value)} />
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function Step4() {
  const [q1, setQ1] = useState(null);
  const [q2, setQ2] = useState(null);
  const blocked = q1 === "yes" || q2 === "yes";
  const clear = q1 === "no" && q2 === "no";

  function YesNoButtons({ value, onChange }) {
    return (
      <div className="flex gap-3 mt-2">
        {["No", "Yes"].map((opt) => {
          const val = opt.toLowerCase();
          const isSelected = value === val;
          let bg = "transparent"; let border = "var(--c-input-border)"; let color = "var(--c-muted)";
          if (isSelected && val === "no") { bg = C.green[50]; border = C.green[600]; color = C.green[700]; }
          if (isSelected && val === "yes") { bg = "#fef2f2"; border = "#f87171"; color = "#b91c1c"; }
          return (
            <button key={opt} onClick={() => onChange(val)}
              className="flex-1 py-3 rounded-xl text-sm font-semibold transition-all duration-200"
              style={{ fontFamily: "var(--f-body)", border: `2px solid ${border}`, background: bg, color }}>{opt}</button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <StepHeader number={4} title="Eligibility" subtitle="Please answer the following to confirm your eligibility." />

      <SectionCard>
        <div className="space-y-7">
          <div>
            <p className="text-sm font-medium" style={{ fontFamily: "var(--f-body)", color: "var(--c-text)" }}>
              Do you currently have any delinquent property taxes in Genesee County? <span className="text-red-500">*</span>
            </p>
            <YesNoButtons value={q1} onChange={setQ1} />
          </div>

          <div>
            <p className="text-sm font-medium" style={{ fontFamily: "var(--f-body)", color: "var(--c-text)" }}>
              Have you lost property to tax foreclosure within the last 5 years? <span className="text-red-500">*</span>
            </p>
            <YesNoButtons value={q2} onChange={setQ2} />
          </div>
        </div>

        {blocked && (
          <div className="mt-6 p-5 rounded-xl animate-fadeIn" style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
            <div className="flex gap-3">
              <Icon name="xCircle" size={20} className="flex-shrink-0 mt-0.5" style={{ color: "#dc2626" }} />
              <div>
                <p className="text-sm font-semibold" style={{ fontFamily: "var(--f-body)", color: "#991b1b" }}>Unable to Continue</p>
                <p className="text-sm mt-1 leading-relaxed" style={{ fontFamily: "var(--f-body)", color: "#b91c1c" }}>
                  Based on your responses, you are not eligible to purchase property through the Land Bank at this time.
                  If you believe this is an error, please contact our office at (810) 257-3088.
                </p>
              </div>
            </div>
          </div>
        )}

        {clear && (
          <div className="mt-6 p-5 rounded-xl animate-fadeIn" style={{ background: C.green[50], border: `1px solid ${C.green[200]}` }}>
            <div className="flex gap-3">
              <Icon name="checkCircle" size={20} className="flex-shrink-0 mt-0.5" style={{ color: C.green[600] }} />
              <div>
                <p className="text-sm font-semibold" style={{ fontFamily: "var(--f-body)", color: C.green[800] }}>Eligible to Proceed</p>
                <p className="text-sm mt-1" style={{ fontFamily: "var(--f-body)", color: C.green[700] }}>
                  You meet the eligibility requirements. Continue to upload your documents.
                </p>
              </div>
            </div>
          </div>
        )}
      </SectionCard>

      {/* Disclaimer at the bottom, quiet tone */}
      <div className="flex items-start gap-2.5 px-1">
        <Icon name="info" size={14} className="flex-shrink-0 mt-0.5" style={{ color: "var(--c-muted)", opacity: 0.6 }} />
        <p className="text-xs leading-relaxed" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
          Per GCLBA policy, applicants with delinquent property taxes in Genesee County or who have previously 
          lost property to tax foreclosure are not eligible to purchase additional properties through the Land Bank. 
          For questions about eligibility, contact our office at{" "}
          <span style={{ fontFamily: "var(--f-mono)", fontSize: 11 }}>(810) 257-3088</span>.
        </p>
      </div>
    </div>
  );
}

function Step5() {
  return (
    <div className="space-y-6">
      <StepHeader number={5} title="Required Documents" subtitle="Upload the required documents for your purchase type." />

      <SectionCard>
        <SectionLabel>Upload Documents</SectionLabel>
        <div className="space-y-5">
          <UploadZone label="Government-Issued Photo ID" />
          <UploadZone label="Proof of Funds (bank statement or equivalent)" />
        </div>
      </SectionCard>

      <div className="flex items-start gap-2.5 px-1">
        <Icon name="lock" size={14} className="flex-shrink-0 mt-0.5" style={{ color: C.blue[600], opacity: 0.7 }} />
        <p className="text-xs leading-relaxed" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
          Documents are transmitted over a secure connection and stored in compliance with government data protection standards.
          Only authorized GCLBA staff can access uploaded files.
        </p>
      </div>
    </div>
  );
}

function Step6() {
  const [ack, setAck] = useState([false, false, false, false]);
  const toggle = (i) => { const n = [...ack]; n[i] = !n[i]; setAck(n); };
  const allChecked = ack.every(Boolean);

  const items = [
    "I understand that all properties are sold AS IS and the GCLBA makes no guarantees as to the condition of the property.",
    "I understand that properties are transferred with a Quit Claim Deed and the GCLBA does not provide title insurance.",
    "I understand I must coordinate with and obtain all permits and inspections required by the local unit of government.",
    "To the best of my knowledge, the information provided in this application is true and in compliance with GCLBA Policies and Procedures.",
  ];

  return (
    <div className="space-y-6">
      <StepHeader number={6} title="Review & Acknowledgments" subtitle="Please review and acknowledge the following terms before submitting." />

      <div className="space-y-3">
        {items.map((text, i) => (
          <button
            key={i} onClick={() => toggle(i)}
            className="w-full flex items-start gap-3.5 p-4 rounded-xl text-left transition-all duration-200"
            style={{
              border: ack[i] ? `2px solid ${C.green[200]}` : "2px solid var(--c-section-border)",
              background: ack[i] ? C.green[50] + "66" : "var(--c-section-bg)",
            }}
          >
            <div className="mt-0.5 w-5 h-5 rounded flex items-center justify-center flex-shrink-0 transition-all duration-200"
              style={{
                border: ack[i] ? "none" : "2px solid #c4beb6",
                background: ack[i] ? C.green[600] : "white",
              }}>
              {ack[i] && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </div>
            <p className="text-sm leading-relaxed" style={{ fontFamily: "var(--f-body)", color: "var(--c-text)" }}>{text}</p>
          </button>
        ))}
      </div>

      {allChecked && (
        <div className="p-5 rounded-xl text-center animate-fadeIn" style={{ background: C.green[50], border: `1px solid ${C.green[200]}` }}>
          <Icon name="checkCircle" size={28} className="mx-auto mb-2" style={{ color: C.green[600] }} />
          <p className="text-sm font-semibold" style={{ fontFamily: "var(--f-body)", color: C.green[800] }}>Ready to Submit</p>
          <p className="text-xs mt-1" style={{ fontFamily: "var(--f-body)", color: C.green[700] }}>
            All acknowledgments confirmed. Click "Submit Application" below.
          </p>
        </div>
      )}
    </div>
  );
}

/* ─── Confirmation ─── */
function ConfirmationScreen() {
  return (
    <div className="gclba-portal min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="max-w-lg w-full text-center">
          <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 animate-scaleIn"
            style={{ background: C.green[50] }}>
            <Icon name="checkCircle" size={40} style={{ color: C.green[600] }} />
          </div>
          
          <h2 className="text-3xl font-bold mb-2" style={{ fontFamily: "var(--f-title)", color: "var(--c-text)" }}>
            Application Submitted
          </h2>
          <p className="font-semibold mb-1" style={{ fontFamily: "var(--f-mono)", fontSize: 15, color: C.green[700] }}>
            GCLBA-2026-0847
          </p>
          <p className="text-sm mb-8" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
            Save this reference number for your records.
          </p>

          <SectionCard className="text-left mb-6">
            <h3 className="text-base font-bold mb-4" style={{ fontFamily: "var(--f-title)", color: "var(--c-text)" }}>What Happens Next</h3>
            <div className="space-y-3">
              {[
                "Our team will review your application within 5 to 7 business days.",
                "We may contact you if additional documents are needed.",
                "You will receive an email when a decision has been made.",
                "If approved, you will have 30 days to close on the property.",
              ].map((text, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5"
                    style={{ fontFamily: "var(--f-mono)", background: i % 2 === 0 ? C.green[50] : C.blue[50], color: i % 2 === 0 ? C.green[700] : C.blue[700] }}>
                    {i + 1}
                  </span>
                  <p className="text-sm leading-relaxed" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>{text}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <div className="p-5 rounded-2xl mb-8" style={{ background: C.blue[50], border: `1px solid ${C.blue[200]}` }}>
            <h3 className="text-sm font-bold mb-2" style={{ fontFamily: "var(--f-title)", color: "var(--c-text)" }}>Application Summary</h3>
            <div className="space-y-1 text-sm" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
              <p>Property: <span className="font-medium" style={{ color: "var(--c-text)" }}>307 Mason St, Flint, MI 48503</span></p>
              <p>Offer: <span className="font-medium" style={{ fontFamily: "var(--f-mono)", fontSize: 13, color: "var(--c-text)" }}>$5,000.00</span></p>
              <p>Program: <span className="font-medium" style={{ color: "var(--c-text)" }}>Featured Homes</span></p>
            </div>
          </div>

          <p className="text-sm" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
            Questions? Contact us at{" "}
            <span style={{ fontFamily: "var(--f-mono)", fontSize: 13 }}>(810) 257-3088</span>
            {" "}or{" "}
            <a href="mailto:offers@thelandbank.org" className="underline underline-offset-2" style={{ fontFamily: "var(--f-mono)", fontSize: 13, color: C.blue[600] }}>
              offers@thelandbank.org
            </a>
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   HEADER / FOOTER / PROGRESS
   ═══════════════════════════════════════════════════════════════ */

function Header() {
  return (
    <header style={{ background: `linear-gradient(135deg, ${C.green[800]} 0%, ${C.green[900]} 60%, ${C.blue[800]} 100%)` }}>
      <div className="max-w-3xl mx-auto px-4 py-5 sm:px-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center"
              style={{ background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <span className="text-white font-bold" style={{ fontFamily: "var(--f-title)", fontSize: 10, lineHeight: 1.1, textAlign: "center" }}>
                GCLBA
              </span>
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight" style={{ fontFamily: "var(--f-title)" }}>
                Genesee County Land Bank
              </h1>
              <p className="text-xs sm:text-sm" style={{ fontFamily: "var(--f-body)", color: "rgba(255,255,255,0.6)" }}>
                Property Purchase Application
              </p>
            </div>
          </div>
          <a href="https://www.thelandbank.org" target="_blank" rel="noopener"
            className="hidden sm:flex items-center gap-1.5 text-xs transition-colors"
            style={{ fontFamily: "var(--f-body)", color: "rgba(255,255,255,0.5)" }}
            onMouseEnter={(e) => e.currentTarget.style.color = "rgba(255,255,255,0.9)"}
            onMouseLeave={(e) => e.currentTarget.style.color = "rgba(255,255,255,0.5)"}>
            thelandbank.org
            <Icon name="externalLink" size={12} />
          </a>
        </div>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer style={{ background: "var(--c-footer-bg)", borderTop: "1px solid var(--c-section-border)" }}>
      <div className="max-w-3xl mx-auto px-4 py-5 sm:px-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
          <div className="flex items-center gap-2">
            <Icon name="lock" size={13} style={{ color: C.blue[600], opacity: 0.6 }} />
            <span>Secure Application Portal</span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap justify-center">
            <span>Genesee County Land Bank Authority</span>
            <span style={{ opacity: 0.3 }}>|</span>
            <span style={{ fontFamily: "var(--f-mono)", fontSize: 11 }}>452 S. Saginaw St., Flint, MI 48502</span>
            <span style={{ opacity: 0.3 }}>|</span>
            <span style={{ fontFamily: "var(--f-mono)", fontSize: 11 }}>(810) 257-3088</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ─── Progress sidebar (desktop) ─── */
function ProgressSidebar({ currentStep, onStepClick }) {
  return (
    <div className="hidden lg:block w-56 flex-shrink-0">
      <div className="sticky top-8">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-4" style={{ fontFamily: "var(--f-mono)", color: C.blue[600] }}>
          Application Progress
        </p>
        <div className="space-y-1">
          {STEPS.map((step) => {
            const isActive = currentStep === step.id;
            const isComplete = currentStep > step.id;
            return (
              <button
                key={step.id}
                onClick={() => step.id <= currentStep && onStepClick(step.id)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-200"
                style={{
                  background: isActive ? C.green[50] : "transparent",
                  border: isActive ? `1px solid ${C.green[200]}` : "1px solid transparent",
                  opacity: !isActive && !isComplete ? 0.45 : 1,
                  cursor: step.id <= currentStep ? "pointer" : "default",
                }}
              >
                <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold transition-colors"
                  style={{
                    fontFamily: "var(--f-mono)",
                    background: isActive ? C.green[700] : isComplete ? C.green[100] : "#e7e2dc",
                    color: isActive ? "white" : isComplete ? C.green[700] : "#a09890",
                  }}>
                  {isComplete ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6L9 17l-5-5"/>
                    </svg>
                  ) : step.id}
                </div>
                <span className="text-sm" style={{
                  fontFamily: "var(--f-body)",
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? C.green[800] : isComplete ? "var(--c-text)" : "var(--c-muted)",
                }}>
                  {step.label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Blue accent sidebar info */}
        <div className="mt-8 p-4 rounded-xl" style={{ background: C.blue[50], border: `1px solid ${C.blue[100]}` }}>
          <p className="text-[11px] font-semibold uppercase tracking-wider mb-2" style={{ fontFamily: "var(--f-mono)", color: C.blue[600] }}>Need Help?</p>
          <p className="text-xs leading-relaxed" style={{ fontFamily: "var(--f-body)", color: C.blue[700] }}>
            Call <span style={{ fontFamily: "var(--f-mono)" }}>(810) 257-3088</span> or visit{" "}
            <a href="https://www.thelandbank.org" className="underline underline-offset-2" target="_blank" rel="noopener">thelandbank.org</a>
          </p>
        </div>
      </div>
    </div>
  );
}

/* ─── Mobile progress ─── */
function MobileProgress({ currentStep }) {
  const pct = ((currentStep - 1) / (STEPS.length - 1)) * 100;
  const step = STEPS.find((s) => s.id === currentStep);
  return (
    <>
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 h-[3px]" style={{ background: "rgba(0,0,0,0.06)" }}>
        <div className="h-full transition-all duration-500 ease-out" style={{ width: `${pct}%`, background: C.green[600] }} />
      </div>
      <div className="lg:hidden fixed top-2.5 left-1/2 z-50" style={{ transform: "translateX(-50%)" }}>
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full shadow-lg"
          style={{ background: "rgba(255,255,255,0.95)", backdropFilter: "blur(8px)", border: "1px solid rgba(0,0,0,0.08)" }}>
          <span className="w-5 h-5 rounded-full text-white flex items-center justify-center text-[10px] font-bold"
            style={{ fontFamily: "var(--f-mono)", background: C.green[700] }}>{currentStep}</span>
          <span className="text-xs font-medium" style={{ fontFamily: "var(--f-body)", color: "var(--c-text)" }}>{step?.shortLabel}</span>
          <span className="text-[10px]" style={{ fontFamily: "var(--f-mono)", color: "var(--c-muted)" }}>{currentStep}/{STEPS.length}</span>
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN APPLICATION
   ═══════════════════════════════════════════════════════════════ */
export default function GCLBAApplication() {
  const [currentStep, setCurrentStep] = useState(1);
  const [submitted, setSubmitted] = useState(false);
  const [saving, setSaving] = useState(false);

  const goNext = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      setSubmitted(true);
      window.scrollTo({ top: 0 });
    }
  };

  const goBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleSave = () => { setSaving(true); setTimeout(() => setSaving(false), 2000); };

  if (submitted) return <ConfirmationScreen />;

  const stepComponents = { 1: Step1, 2: Step2, 3: Step3, 4: Step4, 5: Step5, 6: Step6 };
  const StepComponent = stepComponents[currentStep];

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&family=Vollkorn:ital,wght@0,400;0,600;0,700;0,900;1,400&display=swap');
        
        .gclba-portal {
          --f-title: 'Vollkorn', Georgia, serif;
          --f-body: 'IBM Plex Sans', system-ui, sans-serif;
          --f-mono: 'JetBrains Mono', monospace;
          
          --c-text: #2A2622;
          --c-muted: #7A746C;
          --c-bg: #F2EDE6;
          --c-bg-alt: #EAE4DC;
          --c-section-bg: rgba(255,255,255,0.55);
          --c-section-border: rgba(0,0,0,0.07);
          --c-input-bg: rgba(255,255,255,0.7);
          --c-input-border: #CCC7BF;
          --c-footer-bg: #EAE5DD;
        }
        
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.9); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out; }
        .animate-scaleIn { animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
      `}</style>

      <div className="gclba-portal min-h-screen flex flex-col" style={{ background: "linear-gradient(180deg, var(--c-bg) 0%, var(--c-bg-alt) 100%)" }}>
        <Header />
        <MobileProgress currentStep={currentStep} />
        
        <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-6 lg:py-10">
          <div className="flex gap-10">
            <ProgressSidebar currentStep={currentStep} onStepClick={setCurrentStep} />

            <div className="flex-1 min-w-0">
              {/* Step content - no wrapper card, sections are individual cards */}
              <div className="animate-fadeIn" key={currentStep}>
                <StepComponent />
              </div>

              {/* Navigation */}
              <div className="mt-6 p-4 sm:px-6 rounded-2xl flex items-center justify-between"
                style={{ background: "var(--c-section-bg)", border: "1px solid var(--c-section-border)" }}>
                <div className="flex items-center gap-2">
                  {currentStep > 1 && (
                    <button onClick={goBack}
                      className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
                      style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)" }}>
                      <Icon name="chevronLeft" size={16} /> Back
                    </button>
                  )}
                  <button onClick={handleSave}
                    className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
                    style={{ fontFamily: "var(--f-body)", color: C.blue[600] }}>
                    <Icon name="bookmark" size={15} />
                    {saving ? "Saved!" : "Save Progress"}
                  </button>
                </div>

                <button onClick={goNext}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold text-white shadow-sm transition-all duration-200"
                  style={{ fontFamily: "var(--f-body)", background: C.green[700] }}
                  onMouseEnter={(e) => e.currentTarget.style.background = C.green[800]}
                  onMouseLeave={(e) => e.currentTarget.style.background = C.green[700]}>
                  {currentStep === STEPS.length ? "Submit Application" : "Continue"}
                  {currentStep < STEPS.length && <Icon name="chevronRight" size={16} />}
                </button>
              </div>

              {/* Subtle footer help */}
              <div className="mt-5 text-center">
                <p className="text-xs" style={{ fontFamily: "var(--f-body)", color: "var(--c-muted)", opacity: 0.7 }}>
                  Need help? Call{" "}
                  <span style={{ fontFamily: "var(--f-mono)", fontSize: 11 }}>(810) 257-3088</span>
                  {" "}or email{" "}
                  <a href="mailto:offers@thelandbank.org" className="underline underline-offset-2"
                    style={{ fontFamily: "var(--f-mono)", fontSize: 11, color: C.blue[600] }}>
                    offers@thelandbank.org
                  </a>
                </p>
              </div>
            </div>
          </div>
        </main>

        <Footer />
      </div>
    </>
  );
}
