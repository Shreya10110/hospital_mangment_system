import React, {useEffect,useState} from "react";
import {Building2, HeartPulse, ShieldCheck, Stethoscope, UserRound} from "lucide-react";
import {Link, useNavigate} from "react-router-dom";
import {api} from "../api/client";
import "./registration.css";

const accounts=[
  {value:"patient",label:"Patient",description:"Find hospitals and book doctors",icon:UserRound},
  {value:"doctor",label:"Doctor",description:"Apply to verified hospitals",icon:Stethoscope},
  {value:"hospital",label:"Hospital",description:"Manage doctors and appointments",icon:Building2},
];
const saveSession=data=>{localStorage.setItem("citycare_token",data.access_token);localStorage.setItem("citycare_user",JSON.stringify(data.user))};
const home=role=>role==="admin"?"/admin":role==="doctor"?"/doctor":role==="hospital"?"/hospital":"/dashboard";

export default function RegistrationAuthPage({signup=false}){
  const [accountType,setAccountType]=useState("patient"),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const [hospitals,setHospitals]=useState([]),[hospitalsLoading,setHospitalsLoading]=useState(false);
  const navigate=useNavigate();
  useEffect(()=>{if(!signup||accountType!=="doctor")return;setHospitalsLoading(true);api("/hospitals").then(setHospitals).catch(reason=>setError(reason.message)).finally(()=>setHospitalsLoading(false))},[signup,accountType]);
  const submit=async event=>{
    event.preventDefault();setError("");const form=new FormData(event.currentTarget);
    if(signup&&form.get("password")!==form.get("confirm"))return setError("Passwords do not match.");
    setBusy(true);
    try{
      const credentials={email:form.get("email"),password:form.get("password")};
      if(!signup){const result=await api("/login",{method:"POST",body:JSON.stringify(credentials)});saveSession(result);window.location.assign(home(result.user.role));return}
      const account={first_name:form.get("first_name"),last_name:form.get("last_name"),email:credentials.email,mobile:form.get("mobile"),password:credentials.password};
      if(accountType==="patient"){
        const result=await api("/signup",{method:"POST",body:JSON.stringify(account)});saveSession(result);window.location.assign("/dashboard");
      }else if(accountType==="doctor"){
        const result=await api("/doctors/register",{method:"POST",body:JSON.stringify({...account,qualification:form.get("qualification"),specialization:form.get("specialization"),experience:Number(form.get("experience")),medical_registration_number:form.get("medical_registration_number"),bio:form.get("bio"),consultation_fee:Number(form.get("consultation_fee"))})});saveSession(result);
        await api(`/doctor/hospitals/${form.get("hospital_id")}/apply`,{method:"POST"});
        window.location.assign("/doctor");
      }else{
        const owner=await api("/signup",{method:"POST",body:JSON.stringify(account)});saveSession(owner);
        await api("/hospitals/register",{method:"POST",body:JSON.stringify({name:form.get("hospital_name"),registration_number:form.get("hospital_registration_number"),email:account.email,mobile:account.mobile,address:form.get("address"),city:form.get("city"),state:form.get("state"),pincode:form.get("pincode"),description:form.get("description"),specializations:form.get("specializations").split(",").map(x=>x.trim()).filter(Boolean),facilities:form.get("facilities").split(",").map(x=>x.trim()).filter(Boolean)})});
        const result=await api("/login",{method:"POST",body:JSON.stringify(credentials)});saveSession(result);window.location.assign("/hospital");
      }
    }catch(reason){setError(reason.message)}finally{setBusy(false)}
  };
  return <div className={`auth ${signup?"signup-mode":""}`}>
    <section className="hero"><div className="brand"><span><HeartPulse/></span>CityCare</div><h1>Connected care,<br/><i>properly verified.</i></h1><p>Administrators verify hospitals. Verified doctors apply to hospitals. Patients choose the right hospital and doctor.</p><div className="hero-card"><ShieldCheck/> Secure multi-hospital management</div></section>
    <section className="auth-card"><div><p className="eyebrow">{signup?"CREATE ACCOUNT":"WELCOME BACK"}</p><h2>{signup?"Join the CityCare network":"Sign in to CityCare"}</h2><p className="muted">{signup?"Choose the account that matches your role.":"One secure login for every portal."}</p></div>{error&&<div className="error">{error}</div>}
      <form onSubmit={submit}>{signup&&<><label>Account type</label><div className="role-picker">{accounts.map(({value,label,description,icon:Icon})=><button type="button" key={value} className={accountType===value?"active":""} onClick={()=>{setError("");setAccountType(value)}}><Icon/><span><b>{label}</b><small>{description}</small></span></button>)}</div><div className="two"><label>{accountType==="hospital"?"Owner first name":"First name"}<input name="first_name" required minLength="2"/></label><label>{accountType==="hospital"?"Owner last name":"Last name"}<input name="last_name" required/></label></div></>}
        <label>Email address<input type="email" name="email" required/></label>{signup&&<label>Mobile number<input name="mobile" inputMode="numeric" placeholder="9876543210" minLength="10" maxLength="10" pattern="[0-9]{10}" title="Enter exactly 10 digits" required/></label>}<label>Password<input type="password" name="password" minLength="8" required/></label>{signup&&<label>Confirm password<input type="password" name="confirm" required/></label>}
        {signup&&accountType==="doctor"&&<div className="registration-section"><h3>Professional details</h3><div className="two"><label>Qualification<input name="qualification" required/></label><label>Specialization<input name="specialization" required/></label><label>Experience (years)<input name="experience" type="number" min="0" max="80" required/></label><label>Consultation fee<input name="consultation_fee" type="number" min="0" required/></label></div><label>Medical registration number<input name="medical_registration_number" required/></label><label>Professional bio<textarea name="bio"/></label><label>Hospital you want to join<select name="hospital_id" required disabled={hospitalsLoading||!hospitals.length}><option value="">{hospitalsLoading?"Loading verified hospitals…":hospitals.length?"Select a verified hospital":"No verified hospitals available"}</option>{hospitals.map(hospital=><option value={hospital.id} key={hospital.id}>{hospital.name} — {hospital.city}, {hospital.state}</option>)}</select></label>{!hospitalsLoading&&!hospitals.length&&<p className="form-note warning-note">A doctor account can only be submitted after an administrator has verified at least one hospital.</p>}<p className="form-note">After registration, this hospital receives your application. The hospital can approve it after the admin verifies your medical credentials.</p></div>}
        {signup&&accountType==="hospital"&&<div className="registration-section"><h3>Hospital details</h3><label>Hospital name<input name="hospital_name" required/></label><label>Hospital registration number<input name="hospital_registration_number" required/></label><div className="two"><label>City<input name="city" required/></label><label>State<input name="state" required/></label></div><label>Complete address<textarea name="address" required/></label><label>Pincode<input name="pincode" inputMode="numeric" pattern="[0-9]{6}" required/></label><label>Specializations <small>(comma separated)</small><input name="specializations" required/></label><label>Facilities <small>(comma separated)</small><input name="facilities" required/></label><label>Description<textarea name="description" required/></label><p className="form-note">The hospital remains hidden from patients until an administrator verifies it.</p></div>}
        <button className="primary" disabled={busy}>{busy?"Please wait…":signup?`Create ${accountType} account`:"Sign in"}</button></form><p className="muted center">{signup?"Already registered? ":"New to CityCare? "}<Link to={signup?"/login":"/signup"}>{signup?"Sign in":"Create account"}</Link></p>
    </section>
  </div>
}
