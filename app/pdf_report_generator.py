from fastapi import FastAPI, HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from datetime import datetime
import os
from app.services import shared_state
from app.analysis_utils import analyze_performance_from_json, generate_performance_charts

app = FastAPI()

def create_header(story, interview_data):
    """Create the header section of the report."""
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor('#2C3E50')
    )
    
    story.append(Paragraph("Technical Interview Assessment Report", header_style))
    story.append(Spacer(1, 20))
    
    # Create candidate information table
    data = [
        ["Candidate Name:", interview_data.get("candidate_name", "Anonymous")],
        ["Position:", interview_data.get("role", "Not specified")],
        ["Interview Date:", datetime.now().strftime("%Y-%m-%d")],
        ["Experience Level:", interview_data.get("experience_level", "Not specified")]
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#BDC3C7')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50'))
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))

def create_executive_summary(story, analysis_data):
    """Create the executive summary section."""
    styles = getSampleStyleSheet()
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=15
    )
    
    story.append(Paragraph("Executive Summary", section_title))
    
    # Overall rating and result
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=10
    )
    
    story.append(Paragraph(f"Overall Rating: {analysis_data['overall_rating']}/10", summary_style))
    story.append(Paragraph(f"Final Assessment: {analysis_data['result']}", summary_style))
    story.append(Paragraph(analysis_data['overall_performance'], summary_style))
    story.append(Spacer(1, 20))

def create_skills_section(story, skills):
    """Create the technical skills assessment section."""
    styles = getSampleStyleSheet()
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=15
    )
    
    story.append(Paragraph("Technical Skills Assessment", section_title))
    
    if not skills:
        story.append(Paragraph("No skills assessment available", styles['Normal']))
        return
    
    # Create skills table with modern styling
    data = [["Technical Skill", "Proficiency (0-10)"]]
    for skill, rating in skills.items():
        data.append([skill, f"{rating}/10"])
    
    table = Table(data, colWidths=[4*inch, 2*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#BDC3C7')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))

def create_performance_analysis_section(story, analysis_data):
    """Create the detailed performance analysis section."""
    styles = getSampleStyleSheet()
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=15
    )
    
    story.append(Paragraph("Detailed Performance Analysis", section_title))
    
    # Create category analysis with modern styling
    for category, details in analysis_data['skill_categories'].items():
        # Category header
        category_style = ParagraphStyle(
            'Category',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#2C3E50'),
            spaceBefore=15,
            spaceAfter=10
        )
        story.append(Paragraph(category, category_style))
        
        # Category details
        detail_style = ParagraphStyle(
            'Detail',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=5,
            leading=14  # Add leading to control line spacing
        )
        story.append(Paragraph(f"Rating: {details['rating']}/10", detail_style))
        story.append(Paragraph(f"Evidence: {details['evidence']}", detail_style))
        
        # Subcategories table with adjusted widths and word wrapping
        data = [["Aspect", "Rating", "Observations"]]
        for sub_name, sub_details in details['subcategories'].items():
            # Add word wrapping for evidence text
            evidence_text = Paragraph(sub_details['evidence'], detail_style)
            data.append([
                Paragraph(sub_name, detail_style),
                f"{sub_details['rating']}/10",
                evidence_text
            ])
        
        col_widths = [1.5*inch, 0.8*inch, 3.7*inch]  # Adjusted column widths
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
    
    # Key observations
    story.append(Paragraph("Key Observations", category_style))
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#2C3E50'),
        leftIndent=20,
        spaceAfter=5,
        leading=14  # Add leading to control line spacing
    )
    for point in analysis_data['evidence']:
        story.append(Paragraph(f"• {point}", bullet_style))
    story.append(Spacer(1, 20))

async def generate_pdf_report(interview_id: str):
    """Generate a PDF report for the interview."""
    try:
        # Get interview data
        interview_data = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": interview_id}
        )
        
        if not interview_data:
            raise HTTPException(status_code=404, detail="Interview not found")
            
        # Get conversation history
        conversation_history = interview_data.get("conversation_history", [])
        if not conversation_history:
            raise HTTPException(
                status_code=400,
                detail="No conversation history found. Please complete the interview first."
            )

        # Format conversation history for analysis
        formatted_qa = []
        for entry in conversation_history:
            if isinstance(entry, dict):
                formatted_qa.append({
                    "question": entry.get("question", ""),
                    "answer": entry.get("answer", ""),
                    "skill_assessed": entry.get("skill_assessed", "general"),
                    "technical_depth": entry.get("technical_depth", "basic")
                })
        
        # Generate performance analysis with actual conversation data
        analysis_data = await analyze_performance_from_json({
            "question_answer": formatted_qa,
            "candidate_name": "Candidate",  # Using default name
            "position_applied": interview_data.get("role", "Not specified"),
            "interview_date": datetime.now().strftime("%Y-%m-%d"),
            "interviewer_name": "AI Interviewer",
            "skills_assessment": interview_data.get("skills", {}),  # Include skills ratings
            "technical_assessment": interview_data.get("technical_assessment", {})  # Include any technical assessment
        })
        
        # Create output directory
        output_dir = 'generated_reports'
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{output_dir}/report_{interview_id}_{timestamp}.pdf"
        
        # Create PDF with adjusted margins
        doc = SimpleDocTemplate(
            filename,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        # Build content with actual data
        story = []
        
        # Update interview data with correct information
        report_data = {
            "candidate_name": "Candidate",
            "role": interview_data.get("role", "Not specified"),
            "experience_level": interview_data.get("experience_level", "Not specified"),
            "skills": interview_data.get("skills", {}),
            "conversation_history": formatted_qa,
            "technical_assessment": interview_data.get("technical_assessment", {})
        }
        
        create_header(story, report_data)
        create_executive_summary(story, analysis_data)
        
        # Generate and add charts with actual data
        radar_chart_path, bar_chart_path = generate_performance_charts(analysis_data)
        story.append(Spacer(1, 20))
        story.append(Image(radar_chart_path, width=6*inch, height=6*inch))
        story.append(Spacer(1, 20))
        story.append(Image(bar_chart_path, width=7*inch, height=4*inch))
        story.append(Spacer(1, 20))
        
        create_skills_section(story, report_data["skills"])
        create_performance_analysis_section(story, analysis_data)
        
        # Generate PDF
        doc.build(story)
        
        # Update MongoDB with PDF path and analysis
        await shared_state.mongodb.ai_interviews.update_one(
            {"interview_id": interview_id},
            {"$set": {
                "pdf_report": filename,
                "status": "report_generated",
                "analysis_data": analysis_data
            }}
        )
        
        return {
            "status": "success",
            "message": "PDF report generated successfully",
            "file_path": filename
        }
        
    except Exception as e:
        print(f"Error generating PDF report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/{interview_id}")
async def get_pdf_report(interview_id: str):
    """Get the path to a generated PDF report."""
    try:
        interview_data = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": interview_id}
        )
        
        if not interview_data:
            raise HTTPException(status_code=404, detail="Interview not found")
            
        pdf_path = interview_data.get("pdf_report")
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF report not found")
            
        return {
            "status": "success",
            "file_path": pdf_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 