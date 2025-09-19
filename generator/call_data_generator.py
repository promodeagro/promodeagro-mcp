#!/usr/bin/env python3
"""
Starhub Call Analysis Data Generator

This script generates realistic sample call analysis data for the Starhub reporting system.
It creates call analysis, SFDC actions, and transcript files that match the expected format
for S3 storage and Athena analysis.

Author: AI Assistant
Date: 2025
"""

import json
import random
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any
import uuid
import argparse
from pathlib import Path
import os

class CallDataGenerator:
    def __init__(self, s3_bucket: str = "starhub-totogi-poc"):
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3') if self._has_aws_credentials() else None
        
        # Sample data for generating realistic calls
        self.agents = [
            {"name": "Badri", "id": "agent-001"},
            {"name": "Sarah", "id": "agent-002"}, 
            {"name": "Kumar", "id": "agent-003"},
            {"name": "Lisa", "id": "agent-004"},
            {"name": "Ahmad", "id": "agent-005"}
        ]
        
        self.customers = [
            {"name": "Allen", "email": "allen@singapore-pvt.com", "company": "Singapore Private Limited"},
            {"name": "Kyrie", "email": "kyrie@hnkalpha.com", "company": "HNK Alpha"},
            {"name": "Jennifer", "email": "jen@techcorp.sg", "company": "TechCorp Pte Ltd"},
            {"name": "David", "email": "david@innovate.com", "company": "Innovate Solutions"},
            {"name": "Maria", "email": "maria@globaltech.sg", "company": "Global Tech Systems"}
        ]
        
        self.call_types = [
            "Internet Service Upgrade",
            "New Service Inquiry", 
            "Service Renewal",
            "Technical Support",
            "Billing Inquiry"
        ]
        
        self.grading_elements = [
            {"element": "Greetings & Intro", "weight": 5},
            {"element": "Call Closing", "weight": 5},
            {"element": "Verification & Validation", "weight": 5},
            {"element": "Needs Assessment", "weight": 10},
            {"element": "Product/Service Presentation", "weight": 10},
            {"element": "Objection Handling", "weight": 10},
            {"element": "Sales Tenacity & Determination", "weight": 10},
            {"element": "Closing Technique & Follow-Up", "weight": 10},
            {"element": "Upsell & Cross-sell", "weight": 10},
            {"element": "Clarity of Verbal Expression", "weight": 5},
            {"element": "Active Listening", "weight": 5},
            {"element": "Telephony Skill & Etiquette", "weight": 10},
            {"element": "NPS Prompt", "weight": 10},
            {"element": "Activity Log", "weight": 15},
            {"element": "Opportunity Handling", "weight": 15},
            {"element": "Respond to Customer Queries", "weight": 15}
        ]

    def _has_aws_credentials(self) -> bool:
        """Check if AWS credentials are available"""
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            return credentials is not None
        except:
            return False

    def generate_call_id(self, date: datetime) -> str:
        """Generate a unique call ID"""
        return f"CHR-{date.year}-{random.randint(100, 999):03d}"

    def generate_call_analysis(self, call_id: str, call_date: datetime, agent: Dict, customer: Dict, call_type: str) -> Dict[str, Any]:
        """Generate call analysis JSON matching the expected format with S3 URIs"""
        
        # Calculate grading scores
        grading_elements = []
        total_weighted_score = 0
        total_weight = 0
        
        for element in self.grading_elements:
            score = random.randint(0, 100)
            if element["element"] in ["NPS Prompt", "Activity Log"] and random.random() < 0.3:
                score = 0  # Sometimes these are missed entirely
            
            evidence = self._generate_evidence(element["element"], score)
            
            grading_elements.append({
                "element": element["element"],
                "weight": element["weight"],
                "score": score,
                "evidence": evidence
            })
            
            total_weighted_score += score * element["weight"]
            total_weight += element["weight"]
        
        total_score_percent = round(total_weighted_score / total_weight, 2)
        is_pass = total_score_percent >= 70
        
        # Generate sentiment analysis
        sentiment_progression = [round(random.uniform(0.1, 0.9), 1) for _ in range(5)]
        overall_sentiment = round(sum(sentiment_progression) / len(sentiment_progression), 1)
        
        # Generate S3 URIs for linked files
        s3_base_path = f"s3://{self.s3_bucket}"
        date_partition = f"year={call_date.year}/month={call_date.month:02d}/day={call_date.day:02d}"
        
        return {
            "call_id": call_id,
            "call_date": call_date.isoformat(),
            "transcript_s3_uri": f"{s3_base_path}/transcript/{date_partition}/{call_id}-transcript.json",
            "sfdc_action_s3_uri": f"{s3_base_path}/sfdcaction/{date_partition}/{call_id}-sfdcaction.json",
            "diarized_s3_uri": f"{s3_base_path}/diarized/{date_partition}/{call_id}-diarized.json",
            "transcript_file": f"{call_id}-transcript.json",
            "sfdcaction_file": f"{call_id}-sfdcaction.json",
            "diarized_file": f"{call_id}-diarized.json",
            "agent_name": agent["name"],
            "customer_company": customer["company"],
            "call_duration": f"{random.uniform(5, 25):.1f} minutes",
            "call_type": call_type,
            "compliance": {
                "pdpa_pass": random.choice([True, False]),
                "breaches": [] if random.random() > 0.2 else ["Minor data protection concern"]
            },
            "grading": {
                "total_score_percent": total_score_percent,
                "pass": is_pass,
                "elements": grading_elements
            },
            "qualifying_questions": {
                "asked": self._generate_qualifying_questions(call_type),
                "missed": self._generate_missed_questions(call_type)
            },
            "call_metrics": {
                "talk_to_listen_ratio": round(random.uniform(0.4, 0.8), 2),
                "customer_interruption_count": random.randint(0, 8),
                "silence_periods": random.randint(1, 10),
                "speaking_pace_wpm": random.randint(140, 180),
                "energy_level": round(random.uniform(0.5, 0.95), 2),
                "voice_clarity": round(random.uniform(0.75, 0.98), 2)
            },
            "sentiment_analysis": {
                "overall_sentiment": overall_sentiment,
                "customer_satisfaction": round(random.uniform(0.3, 0.9), 1),
                "sentiment_progression": sentiment_progression,
                "key_sentiment_moments": self._generate_sentiment_moments()
            },
            "script_adherence": {
                "adherence_percentage": random.randint(65, 95),
                "missed_elements": self._generate_missed_elements(),
                "well_executed": self._generate_well_executed_elements()
            },
            "recommendations": self._generate_recommendations(total_score_percent),
            "deal_potential": {
                "estimated_value": random.randint(25000, 150000),
                "probability": round(random.uniform(0.3, 0.9), 2),
                "risk_factors": self._generate_risk_factors(),
                "next_steps": self._generate_next_steps(call_type)
            }
        }

    def generate_sfdc_action(self, call_id: str, customer: Dict, call_type: str) -> Dict[str, Any]:
        """Generate SFDC action JSON matching the expected format"""
        
        action_types = {
            "Service Renewal": "service_renewal",
            "New Service Inquiry": "new_inquiry", 
            "Internet Service Upgrade": "service_upgrade",
            "Technical Support": "support_case",
            "Billing Inquiry": "billing_inquiry"
        }
        
        segments = ["New Customer", "Existing Customer", "VIP Customer"]
        customer_segment = random.choice(segments)
        
        return {
            "metadata": {
                "callId": call_id,
                "processedDate": datetime.now().isoformat(),
                "processedBy": "BSS Magic Studio",
                "actionType": action_types.get(call_type, "general_inquiry"),
                "status": "completed",
                "customer": {
                    "name": customer["name"],
                    "email": customer["email"],
                    "company": customer["company"],
                    "segment": customer_segment
                },
                "serviceType": call_type,
                "scenario": self._generate_scenario(call_type)
            },
            "validation": {
                "companyNameVerified": True,
                "businessRegistrationNumber": "obtained" if random.random() > 0.3 else "not_provided",
                "contactDetailsConfirmed": True,
                "email": customer["email"],
                "revenueFlag": "Existing revenue customer" if customer_segment != "New Customer" else "New customer",
                "customerSegment": customer_segment,
                "productRequirements": self._generate_product_requirements(call_type),
                "serviceWithinCapabilities": True,
                "mandatorySalesforceFields": "complete",
                "followUpScheduled": self._generate_follow_up_info(call_type),
                "validationStatus": "passed"
            },
            "action": {
                "searchResults": {
                    "existingContact": {
                        "found": customer_segment != "New Customer",
                        "email": customer["email"],
                        "recordId": f"003XX{random.randint(100000, 999999):06d}" if customer_segment != "New Customer" else None
                    },
                    "existingAccount": {
                        "found": customer_segment != "New Customer",
                        "name": customer["company"],
                        "recordId": f"001XX{random.randint(100000, 999999):06d}" if customer_segment != "New Customer" else None
                    }
                },
                "recordsCreated": self._generate_records_created(call_type, customer_segment),
                "recordsUpdated": self._generate_records_updated(customer_segment),
                "nextActions": self._generate_next_actions(call_type),
                "totalRecordsAffected": random.randint(1, 4),
                "actionStatus": "success"
            }
        }

    def generate_transcript(self, call_id: str, agent: Dict, customer: Dict, call_type: str) -> Dict[str, Any]:
        """Generate transcript JSON matching the expected format"""
        
        # Generate conversation turns based on call type
        turns = self._generate_conversation_turns(agent, customer, call_type)
        
        return {
            "transcript": turns
        }
    
    def generate_diarized(self, call_id: str, call_date: datetime, agent: Dict, customer: Dict, call_type: str) -> Dict[str, Any]:
        """Generate diarized JSON data with speaker segmentation and sentiment"""
        
        # Generate realistic call duration in seconds
        duration_seconds = random.randint(300, 1500)  # 5-25 minutes
        duration_minutes = round(duration_seconds / 60, 2)
        
        # Generate segments based on conversation flow
        segments = self._generate_diarized_segments(agent, customer, call_type, duration_seconds)
        
        return {
            "metadata": {
                "version": "1.0",
                "format": "starhub-diarized-transcript",
                "created_at": datetime.now().isoformat() + "Z",
                "call_id": call_id,
                "agent_name": agent["name"],
                "customer_company": customer["company"],
                "call_duration_seconds": duration_seconds,
                "call_duration_formatted": f"{duration_minutes} minutes",
                "call_type": call_type,
                "call_date": call_date.isoformat() + "Z"
            },
            "segments": segments
        }

    def _generate_conversation_turns(self, agent: Dict, customer: Dict, call_type: str) -> List[Dict]:
        """Generate realistic conversation turns"""
        
        templates = {
            "Internet Service Upgrade": [
                {"speaker": "agent", "content": f"Hello? Hi, good afternoon. This is {agent['name']}. I'm calling from Starhub Enterprise sales. May I speak to Mr. {customer['name']}?"},
                {"speaker": "customer", "content": "Yes, speaking."},
                {"speaker": "agent", "content": f"Hi Mr. {customer['name']}. I'm giving you a call regarding your inquiry for internet services. Is it a good time to talk?"},
                {"speaker": "customer", "content": "Sure, go ahead."},
                {"speaker": "agent", "content": "Great! I wanted to understand more about your requirements. What bandwidth are you currently using?"},
                {"speaker": "customer", "content": "We're currently on 200 Mbps but we're looking to upgrade to higher bandwidth."},
                {"speaker": "agent", "content": "Perfect. We have options for 300, 400, and 500 Mbps. What contract length would you prefer?"},
                {"speaker": "customer", "content": "We'll need to check with finance. Can you provide quotes for both 24 and 36 months?"},
                {"speaker": "agent", "content": "Absolutely. Do you have any specific IP address requirements?"},
                {"speaker": "customer", "content": "No special requirements, just a standard bundle should work."},
                {"speaker": "agent", "content": "I'll send you the quotations. Can I confirm your email address?"},
                {"speaker": "customer", "content": f"Yes, it's {customer['email']}."},
                {"speaker": "agent", "content": "Perfect. I'll send this over today and follow up with you. Thank you for your time!"}
            ],
            "Service Renewal": [
                {"speaker": "agent", "content": f"Hi {customer['name']}, this is {agent['name']} from Starhub. How are you today?"},
                {"speaker": "customer", "content": "Good, thanks. What can I help you with?"},
                {"speaker": "agent", "content": "I'm calling about your broadband service renewal. Your current contract is expiring soon."},
                {"speaker": "customer", "content": "Right, we've been happy with the service. What are our options?"},
                {"speaker": "agent", "content": "We can offer you the same package or upgrade to higher bandwidth at competitive rates."},
                {"speaker": "customer", "content": "What would an upgrade cost us?"},
                {"speaker": "agent", "content": "Let me prepare a comparison for you. Are you interested in maintaining the same contract term?"},
                {"speaker": "customer", "content": "Yes, 36 months should be fine."},
                {"speaker": "agent", "content": "Excellent. I'll send over the renewal options and we can schedule a follow-up call."}
            ]
        }
        
        base_turns = templates.get(call_type, templates["Internet Service Upgrade"])
        turns = []
        
        timestamp = 0
        for i, turn in enumerate(base_turns):
            duration = random.randint(5, 30)
            turns.append({
                "turnId": i + 1,
                "speaker": turn["speaker"],
                "speakerId": agent["id"] if turn["speaker"] == "agent" else "customer-001",
                "timestamp": self._format_timestamp(timestamp),
                "duration": self._format_timestamp(duration),
                "content": turn["content"],
                "confidence": round(random.uniform(0.85, 0.98), 2)
            })
            timestamp += duration
        
        return turns

    def _format_timestamp(self, seconds: int) -> str:
        """Format seconds to MM:SS format"""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}:{random.randint(0, 59):02d}"

    def _generate_evidence(self, element: str, score: int) -> str:
        """Generate evidence text for grading elements"""
        evidence_templates = {
            "Greetings & Intro": {
                75: "Professional greeting but missed some key introduction elements.",
                100: "Excellent greeting with proper introduction and courtesy.",
                50: "Basic greeting but lacked professionalism.",
                0: "Poor or missing greeting."
            },
            "Call Closing": {
                75: "Thanked customer but missed explicit next steps.",
                100: "Perfect closing with thanks, next steps, and final check.",
                50: "Abrupt closing without proper thanks or follow-up.",
                0: "No proper closing."
            }
        }
        
        if element in evidence_templates:
            score_bucket = min(evidence_templates[element].keys(), key=lambda x: abs(x - score))
            return evidence_templates[element][score_bucket]
        
        return f"Score reflects performance in {element.lower()}."

    def _generate_qualifying_questions(self, call_type: str) -> List[Dict]:
        """Generate qualifying questions asked during the call"""
        questions = {
            "Internet Service Upgrade": [
                {"question": "What is your current bandwidth?", "answer": "Currently using 200 Mbps dedicated line."},
                {"question": "What contract length are you considering?", "answer": "Finance will decide between 24 and 36 months."},
                {"question": "Do you have specific IP requirements?", "answer": "No specific requirements, standard bundle is fine."}
            ],
            "Service Renewal": [
                {"question": "Are you satisfied with current service?", "answer": "Yes, very satisfied with performance."},
                {"question": "Any changes needed for renewal?", "answer": "Same package is fine, maybe slight upgrade if cost-effective."}
            ]
        }
        
        return questions.get(call_type, questions["Internet Service Upgrade"])

    def _generate_missed_questions(self, call_type: str) -> List[str]:
        """Generate questions that should have been asked"""
        missed = {
            "Internet Service Upgrade": [
                "What is your current pain point with existing service?",
                "What is your budget range for the upgrade?"
            ],
            "Service Renewal": [
                "Any upcoming business changes that might affect bandwidth needs?",
                "Have you experienced any service issues we should address?"
            ]
        }
        
        return missed.get(call_type, missed["Internet Service Upgrade"])

    def _generate_sentiment_moments(self) -> List[Dict]:
        """Generate key sentiment moments during the call"""
        moments = [
            {
                "timestamp": f"{random.randint(1, 5)}:{random.randint(10, 59)}",
                "sentiment": round(random.uniform(0.6, 0.9), 1),
                "context": "Customer expressed interest in upgrade options"
            },
            {
                "timestamp": f"{random.randint(6, 12)}:{random.randint(10, 59)}",
                "sentiment": round(random.uniform(0.2, 0.5), 1),
                "context": "Customer showed concern about pricing"
            }
        ]
        
        return random.sample(moments, k=random.randint(1, 2))

    def _generate_missed_elements(self) -> List[str]:
        """Generate missed script elements"""
        elements = [
            "Did not confirm customer's business needs upfront",
            "Missed opportunity to present value proposition early",
            "Could have asked more qualifying questions",
            "Did not establish urgency or timeline"
        ]
        
        return random.sample(elements, k=random.randint(1, 3))

    def _generate_well_executed_elements(self) -> List[str]:
        """Generate well-executed script elements"""
        elements = [
            "Professional greeting and introduction",
            "Technical knowledge demonstration", 
            "Follow-up commitment",
            "Active listening skills",
            "Clear product explanation"
        ]
        
        return random.sample(elements, k=random.randint(2, 4))

    def _generate_recommendations(self, score: float) -> List[str]:
        """Generate recommendations based on performance score"""
        if score >= 80:
            return [
                "Excellent performance, maintain current approach",
                "Consider mentoring junior team members"
            ]
        elif score >= 70:
            return [
                "Good performance with room for improvement",
                "Focus on closing techniques",
                "Work on qualifying questions"
            ]
        else:
            return [
                "Needs significant improvement in sales process",
                "Recommend additional training on qualifying questions",
                "Practice objection handling techniques",
                "Focus on script adherence"
            ]

    def _generate_risk_factors(self) -> List[str]:
        """Generate deal risk factors"""
        factors = [
            "Price sensitivity",
            "Decision timeline unclear", 
            "Multiple stakeholders in decision process",
            "Budget constraints mentioned",
            "Comparing with competitors"
        ]
        
        return random.sample(factors, k=random.randint(1, 3))

    def _generate_next_steps(self, call_type: str) -> List[str]:
        """Generate next steps based on call type"""
        steps = {
            "Internet Service Upgrade": [
                "Send quotation with multiple options",
                "Schedule follow-up call in 3-5 days"
            ],
            "Service Renewal": [
                "Send renewal contract", 
                "Schedule contract review meeting"
            ]
        }
        
        return steps.get(call_type, ["Send information", "Follow up next week"])
    
    def _generate_diarized_segments(self, agent: Dict, customer: Dict, call_type: str, total_duration: int) -> List[Dict]:
        """Generate realistic diarized segments with timestamps and sentiment"""
        
        segments = []
        current_time = 0.0
        segment_id = 1
        
        # Common phrases for different speakers and call phases
        agent_phrases = [
            "Good morning!", f"This is {agent['name']}.", "Calling from StarHub.",
            "How can I help you today?", "Let me check that for you.", "I understand your concern.",
            "We have several options available.", "Would you be interested in...", 
            "Let me send you the details.", "Is there anything else I can help with?",
            "Thank you for your time.", "Have a wonderful day!", "Goodbye!"
        ]
        
        customer_phrases = [
            "Good morning.", "Hello.", "Yes, I'm interested.", "What are the options?",
            "How much would that cost?", "I need to think about it.", "Can you send me the details?",
            "That sounds good.", "What's the next step?", "Thank you.", "Goodbye!"
        ]
        
        # Generate opening exchange
        for i in range(3):
            if i % 2 == 0:  # Agent speaks first
                text = agent_phrases[i] if i < len(agent_phrases) else "Thank you for calling."
                speaker = "agent"
                sentiment = round(random.uniform(0.6, 0.9), 1)
            else:
                text = customer_phrases[min(i//2, len(customer_phrases)-1)]
                speaker = "customer"
                sentiment = round(random.uniform(0.4, 0.7), 1)
            
            duration = random.uniform(2.0, 5.0)
            segments.append({
                "id": segment_id,
                "start_time": round(current_time, 1),
                "end_time": round(current_time + duration, 1),
                "speaker": speaker,
                "text": text,
                "sentiment": sentiment
            })
            current_time += duration
            segment_id += 1
        
        # Generate middle conversation (main discussion)
        middle_duration = total_duration - current_time - 60  # Leave 60 seconds for closing
        turns = random.randint(8, 16)
        
        for i in range(turns):
            speaker = "agent" if i % 2 == 0 else "customer"
            
            if speaker == "agent":
                text = random.choice(agent_phrases[3:10])  # Middle conversation phrases
                sentiment = round(random.uniform(0.5, 0.8), 1)
            else:
                text = random.choice(customer_phrases[2:8])  # Customer responses
                sentiment = round(random.uniform(0.2, 0.7), 1)
                
            duration = random.uniform(3.0, middle_duration / turns)
            segments.append({
                "id": segment_id,
                "start_time": round(current_time, 1),
                "end_time": round(current_time + duration, 1),
                "speaker": speaker,
                "text": text,
                "sentiment": sentiment
            })
            current_time += duration
            segment_id += 1
        
        # Generate closing exchange
        closing_phrases = [("agent", "Is there anything else I can help with?", 0.7),
                          ("customer", "No, that covers everything.", 0.6),
                          ("agent", "Thank you for your time!", 0.8),
                          ("customer", "Thank you. Goodbye!", 0.7),
                          ("agent", "Goodbye!", 0.8)]
        
        for speaker, text, sentiment in closing_phrases:
            duration = random.uniform(2.0, 4.0)
            if current_time + duration <= total_duration:
                segments.append({
                    "id": segment_id,
                    "start_time": round(current_time, 1),
                    "end_time": round(current_time + duration, 1),
                    "speaker": speaker,
                    "text": text,
                    "sentiment": sentiment
                })
                current_time += duration
                segment_id += 1
        
        return segments

    def _generate_scenario(self, call_type: str) -> str:
        """Generate scenario description"""
        scenarios = {
            "Internet Service Upgrade": "Existing customer seeking bandwidth upgrade with specific technical requirements",
            "Service Renewal": "Renewal/upgrade, existing customer, strong interest, clear requirements",
            "New Service Inquiry": "New potential customer exploring service options"
        }
        
        return scenarios.get(call_type, "General service inquiry")

    def _generate_product_requirements(self, call_type: str) -> str:
        """Generate product requirements"""
        requirements = {
            "Internet Service Upgrade": f"{random.choice([300, 400, 500])} Mbps broadband upgrade with static IP",
            "Service Renewal": f"{random.choice([200, 300, 500])} Mbps broadband renewal with static IP",
            "New Service Inquiry": f"{random.choice([100, 200, 300])} Mbps new broadband connection"
        }
        
        return requirements.get(call_type, "Standard broadband service")

    def _generate_follow_up_info(self, call_type: str) -> str:
        """Generate follow-up information"""
        info = {
            "Internet Service Upgrade": "Quotation to be sent, follow-up call scheduled",
            "Service Renewal": "Contract and process explained",
            "New Service Inquiry": "Information package to be provided"
        }
        
        return info.get(call_type, "Follow-up scheduled")

    def _generate_records_created(self, call_type: str, segment: str) -> Dict:
        """Generate records created in Salesforce"""
        records = {
            "opportunities": {"count": 0, "records": []},
            "leads": {"count": 0, "records": []}, 
            "contacts": {"count": 0, "records": []},
            "accounts": {"count": 0, "records": []},
            "notes": {"count": 0, "records": []}
        }
        
        if segment == "New Customer":
            records["leads"]["count"] = 1
            records["leads"]["records"] = [{
                "id": f"00Q{random.randint(10000, 99999):05d}",
                "name": f"New {call_type} Lead",
                "status": "New",
                "url": f"https://yourorg.salesforce.com/00Q{random.randint(10000, 99999):05d}"
            }]
        else:
            records["opportunities"]["count"] = 1
            records["opportunities"]["records"] = [{
                "id": f"006XX{random.randint(100000, 999999):06d}",
                "name": f"{call_type} Opportunity",
                "stage": "Qualification",
                "url": f"https://yourorg.salesforce.com/006XX{random.randint(100000, 999999):06d}"
            }]
        
        return records

    def _generate_records_updated(self, segment: str) -> Dict:
        """Generate records updated in Salesforce"""
        if segment == "New Customer":
            return {"contacts": {"count": 0}}
        
        return {
            "contacts": {
                "count": 1,
                "records": [{
                    "id": f"003XX{random.randint(100000, 999999):06d}",
                    "fields": ["LastCallDate", "ServiceInterest", "LeadSource"]
                }]
            }
        }

    def _generate_next_actions(self, call_type: str) -> List[Dict]:
        """Generate next actions"""
        base_date = datetime.now() + timedelta(days=1)
        
        actions = {
            "Internet Service Upgrade": [
                {"action": "prepare_quotation", "dueDate": base_date.strftime("%Y-%m-%d"), "priority": "high"},
                {"action": "follow_up_call", "dueDate": (base_date + timedelta(days=3)).strftime("%Y-%m-%d"), "priority": "high"}
            ],
            "Service Renewal": [
                {"action": "prepare_renewal_contract", "dueDate": base_date.strftime("%Y-%m-%d"), "priority": "high"},
                {"action": "schedule_contract_review", "dueDate": (base_date + timedelta(days=2)).strftime("%Y-%m-%d"), "priority": "medium"}
            ]
        }
        
        return actions.get(call_type, [{"action": "follow_up", "dueDate": base_date.strftime("%Y-%m-%d"), "priority": "medium"}])

    def generate_s3_path(self, date: datetime, data_type: str) -> str:
        """Generate S3 path with partitioning for different data types"""
        return f"{data_type}/year={date.year}/month={date.month:02d}/day={date.day:02d}/"

    def save_locally(self, data: Dict, filename: str, output_dir: str = "output"):
        """Save data to local JSON file"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        file_path = output_path / filename
        with open(file_path, 'w') as f:
            json.dump(data, f, separators=(',', ':'))
        
        print(f"Saved {filename} to {file_path}")

    def upload_to_s3(self, data: Dict, s3_key: str):
        """Upload data to S3"""
        if not self.s3_client:
            print("AWS credentials not available, skipping S3 upload")
            return
        
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json.dumps(data, separators=(',', ':')),
                ContentType='application/json'
            )
            print(f"Uploaded to s3://{self.s3_bucket}/{s3_key}")
        except Exception as e:
            print(f"Failed to upload to S3: {str(e)}")

    def generate_call_records(self, num_calls: int = 10, days_back: int = 7, save_local: bool = False, upload_s3: bool = True):
        """Generate multiple call records with updated S3 structure"""
        print(f"Generating {num_calls} call records for the last {days_back} days...")
        
        for i in range(num_calls):
            # Random date within the specified range
            call_date = datetime.now() - timedelta(days=random.randint(0, days_back))
            
            # Random selections
            agent = random.choice(self.agents)
            customer = random.choice(self.customers)
            call_type = random.choice(self.call_types)
            call_id = self.generate_call_id(call_date)
            
            print(f"Generating call {i+1}/{num_calls}: {call_id} - {agent['name']} -> {customer['company']}")
            
            # Generate all four data files
            analysis_data = self.generate_call_analysis(call_id, call_date, agent, customer, call_type)
            sfdc_data = self.generate_sfdc_action(call_id, customer, call_type)
            transcript_data = self.generate_transcript(call_id, agent, customer, call_type)
            diarized_data = self.generate_diarized(call_id, call_date, agent, customer, call_type)
            
            # File names
            analysis_file = f"{call_id}-analysis.json"
            sfdc_file = f"{call_id}-sfdcaction.json"
            transcript_file = f"{call_id}-transcript.json"
            diarized_file = f"{call_id}-diarized.json"
            
            if save_local:
                # Create separate directories for each data type
                for data_type in ["analysis", "transcript", "sfdcaction", "diarized"]:
                    local_dir = f"output/{self.generate_s3_path(call_date, data_type)}"
                    Path(local_dir).mkdir(parents=True, exist_ok=True)
                
                self.save_locally(analysis_data, analysis_file, f"output/{self.generate_s3_path(call_date, 'analysis')}")
                self.save_locally(sfdc_data, sfdc_file, f"output/{self.generate_s3_path(call_date, 'sfdcaction')}")
                self.save_locally(transcript_data, transcript_file, f"output/{self.generate_s3_path(call_date, 'transcript')}")
                self.save_locally(diarized_data, diarized_file, f"output/{self.generate_s3_path(call_date, 'diarized')}")
            
            if upload_s3:
                # Store different file types in separate top-level folders as per architecture
                self.upload_to_s3(analysis_data, self.generate_s3_path(call_date, "analysis") + analysis_file)
                self.upload_to_s3(sfdc_data, self.generate_s3_path(call_date, "sfdcaction") + sfdc_file)
                self.upload_to_s3(transcript_data, self.generate_s3_path(call_date, "transcript") + transcript_file)
                self.upload_to_s3(diarized_data, self.generate_s3_path(call_date, "diarized") + diarized_file)
            elif not save_local:
                # Skip this call if neither save_local nor upload_s3 is enabled
                print(f"⚠️  Skipping call {call_id} - no output destination specified")
        
        print(f"\nCompleted generating {num_calls} call records!")
        if save_local:
            print(f"Local files saved in: ./output/")
        if upload_s3:
            print(f"Files uploaded to: s3://{self.s3_bucket}/ (analysis, transcript, sfdcaction, diarized folders)")
        elif not save_local:
            print("⚠️  No output generated - both local and S3 saving disabled")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Starhub call analysis data",
        epilog="Default behavior: Upload to S3 only (no local files). Use --save-local to also save locally."
    )
    parser.add_argument("--num-calls", type=int, default=10, help="Number of call records to generate")
    parser.add_argument("--days-back", type=int, default=7, help="Generate calls for the last N days")
    parser.add_argument("--s3-bucket", type=str, default="starhub-totogi-poc", help="S3 bucket name")
    parser.add_argument("--save-local", action="store_true", help="Save files locally in addition to S3")
    parser.add_argument("--local-only", action="store_true", help="Only save locally, don't upload to S3")
    parser.add_argument("--no-s3", action="store_true", help="Disable S3 upload (only effective with --save-local)")
    
    args = parser.parse_args()
    
    generator = CallDataGenerator(s3_bucket=args.s3_bucket)
    
    # Determine save and upload settings based on arguments
    if args.local_only:
        save_local = True
        upload_s3 = False
    elif args.no_s3:
        save_local = args.save_local  # Must be True if no_s3 is used
        upload_s3 = False
        if not save_local:
            print("❌ Error: --no-s3 requires --save-local to have any output")
            return
    else:
        save_local = args.save_local  # False by default
        upload_s3 = True  # True by default
    
    print(f"📝 Configuration:")
    print(f"   Save locally: {'Yes' if save_local else 'No'}")
    print(f"   Upload to S3: {'Yes' if upload_s3 else 'No'}")
    print(f"   S3 bucket: {args.s3_bucket}")
    print()
    
    generator.generate_call_records(
        num_calls=args.num_calls,
        days_back=args.days_back,
        save_local=save_local,
        upload_s3=upload_s3
    )

if __name__ == "__main__":
    main()
