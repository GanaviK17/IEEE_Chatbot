import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak

OUTPUT_PDF_PATH = os.path.join(os.path.dirname(__file__), "ieee_official_guide.pdf")

def generate_ieee_pdf(output_path=OUTPUT_PDF_PATH):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles adhering to IEEE brand identity
    title_style = ParagraphStyle(
        'IEEETitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#002855'), # IEEE Navy Blue
        spaceAfter=10
    )
    
    h1_style = ParagraphStyle(
        'IEEEH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#00629B'), # IEEE Cerulean Blue
        spaceBefore=12,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'IEEEH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#002855'),
        spaceBefore=8,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'IEEEBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#212529'),
        spaceAfter=7
    )
    
    bullet_style = ParagraphStyle(
        'IEEEBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#333333'),
        leftIndent=15,
        spaceAfter=4
    )
    
    source_tag_style = ParagraphStyle(
        'IEEESource',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#6c757d'),
        spaceBefore=10
    )

    story = []

    # ================= PAGE 1 =================
    story.append(Paragraph("IEEE Official Guide: Organization, History & Structure", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#00629B'), spaceAfter=12))
    
    story.append(Paragraph("1. Mission and Overview", h1_style))
    story.append(Paragraph(
        "The Institute of Electrical and Electronics Engineers (IEEE) is the world's largest technical professional "
        "organization dedicated to advancing technology for the benefit of humanity. IEEE fosters technological innovation "
        "and excellence for the benefit of humanity. As of 2026, IEEE has over 460,000 members across more than 160 countries, "
        "including more than 120,000 student and graduate student members worldwide.",
        body_style
    ))
    
    story.append(Paragraph("2. History and Foundation", h1_style))
    story.append(Paragraph(
        "IEEE was formed on January 1, 1963, through the merger of two prominent engineering organizations: "
        "the American Institute of Electrical Engineers (AIEE), established in 1884 with notable founders including "
        "Thomas Alva Edison, Alexander Graham Bell, and Norvin Green; and the Institute of Radio Engineers (IRE), "
        "founded in 1912 by John Stone Stone, Alfred N. Goldsmith, and Robert H. Marriott. "
        "The merger combined AIEE's deep focus on electric power and light with IRE's expertise in telecommunications and electronics.",
        body_style
    ))
    
    story.append(Paragraph("3. Global Headquarters and Facilities", h1_style))
    story.append(Paragraph(
        "IEEE maintains its corporate headquarters in New York City, New York, United States, and its primary global Operations "
        "Center in Piscataway, New Jersey. In addition, IEEE operates regional offices in Europe, Asia-Pacific, China, and Latin America.",
        body_style
    ))

    story.append(Paragraph("4. Regional Organization (The 10 IEEE Regions)", h1_style))
    story.append(Paragraph(
        "Geographically, IEEE divides the world into 10 administrative Regions: Regions 1 through 6 encompass the United States; "
        "Region 7 represents Canada; Region 8 spans Europe, the Middle East, and Africa; Region 9 covers Latin America and the Caribbean; "
        "and Region 10 covers the Asia-Pacific territory. Each region is further structured into local Sections, Chapters, and Student Branches.",
        body_style
    ))
    story.append(Paragraph("Source: Official IEEE Organizational Charters and History Archives (https://www.ieee.org/about/)", source_tag_style))
    
    story.append(PageBreak())

    # ================= PAGE 2 =================
    story.append(Paragraph("IEEE Membership Grades & Student Benefits", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#00629B'), spaceAfter=12))

    story.append(Paragraph("1. IEEE Membership Grades", h1_style))
    story.append(Paragraph(
        "IEEE offers several membership grades designed to support professionals at each stage of their technical journey:",
        body_style
    ))
    story.append(Paragraph("• <b>Student Member:</b> Undergraduate or graduate students pursuing an accredited engineering or computing degree, registered for at least 50 percent of a full-time study load.", bullet_style))
    story.append(Paragraph("• <b>Graduate Student Member:</b> Students enrolled in graduate study (Master's or Ph.D.) in an IEEE-designated technical field.", bullet_style))
    story.append(Paragraph("• <b>Member:</b> Open to professionals who have graduated with an accredited degree in electrical, electronics, computing, or related scientific disciplines.", bullet_style))
    story.append(Paragraph("• <b>Senior Member:</b> The highest grade for which application can be submitted. Requires at least 10 years of professional practice with 5 years of significant performance and technical leadership.", bullet_style))
    story.append(Paragraph("• <b>IEEE Fellow:</b> An honorary distinction conferred by the IEEE Board of Directors upon a person with an extraordinary record of accomplishments. Less than 0.1% of voting members are elevated to Fellow annually.", bullet_style))
    story.append(Paragraph("• <b>Life Member:</b> Awarded to members who have reached at least 65 years of age and whose age plus years of continuous membership equals at least 100.", bullet_style))

    story.append(Paragraph("2. Exclusive IEEE Student Member Benefits", h1_style))
    story.append(Paragraph(
        "IEEE Student and Graduate Student Members receive substantial global benefits including:",
        body_style
    ))
    story.append(Paragraph("• <b>IEEE Spectrum Subscription:</b> Monthly digital and print access to the premier flagship magazine covering emerging technology trends.", bullet_style))
    story.append(Paragraph("• <b>IEEE Potentials Magazine:</b> Dedicated publication focusing on student engineering career development, technical innovation, and career advice.", bullet_style))
    story.append(Paragraph("• <b>IEEE @ieee.org Email Alias:</b> Complimentary professional email alias forwarding with Google Workspace and cloud spam protection.", bullet_style))
    story.append(Paragraph("• <b>Career Resources & ResumeLab:</b> Access to the IEEE Job Site, Mentoring360 networking platform, and the IEEE ResumeLab builder.", bullet_style))
    story.append(Paragraph("• <b>Technical Society Discount:</b> Students receive approximately 50% discount on joining any of IEEE's 39 technical societies.", bullet_style))
    story.append(Paragraph("• <b>Conference Registration Discounts:</b> Steeply discounted student rates at over 1,900 IEEE international conferences each year.", bullet_style))
    story.append(Paragraph("Source: IEEE Member & Student Advantage Program (https://www.ieee.org/membership/)", source_tag_style))

    story.append(PageBreak())

    # ================= PAGE 3 =================
    story.append(Paragraph("IEEE Student Branches & Flagship Competitions", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#00629B'), spaceAfter=12))

    story.append(Paragraph("1. Establishing and Operating an IEEE Student Branch", h1_style))
    story.append(Paragraph(
        "An IEEE Student Branch provides a hub of technical innovation, mentorship, and leadership development on university campuses. "
        "To establish a recognized Student Branch, a university must have a petition signed by a minimum of 12 IEEE Student Members, "
        "endorsement by the Department Chair, and an appointed IEEE Branch Counselor who is a faculty member and active IEEE Member. "
        "The Branch Executive Committee consists of Chair, Vice-Chair, Secretary, and Treasurer.",
        body_style
    ))
    story.append(Paragraph(
        "To maintain active status and qualify for annual financial rebates from IEEE Headquarters, each Branch must submit "
        "an annual activity report and new officer election reports by the established regional deadline.",
        body_style
    ))

    story.append(Paragraph("2. Annual Flagship Student Competitions & Events", h1_style))
    story.append(Paragraph("• <b>IEEEXtreme:</b> A world-renowned 24-hour virtual competitive programming competition held annually on the fourth Saturday of October. Student teams solve algorithmic programming challenges proctored by an IEEE member.", bullet_style))
    story.append(Paragraph("• <b>IEEE Day:</b> Celebrated globally on the first Tuesday of October to commemorate the historic 1884 gathering of engineers that birthed IEEE. Student Branches organize technical workshops, hackathons, and outreach.", bullet_style))
    story.append(Paragraph("• <b>IEEE SIGHT (Special Interest Group on Humanitarian Technology):</b> A global network of IEEE volunteers partnering with local underserved communities to co-design and implement sustainable technology solutions.", bullet_style))
    story.append(Paragraph("• <b>IEEE Student Project Contests & Grants:</b> IEEE Sections Congress, Region 10 SAC awards, and IEEE Foundation grants provide funding for student hardware innovation and humanitarian projects.", bullet_style))

    story.append(Paragraph("Source: IEEE Student Activities Committee (SAC) Operations Manual (https://students.ieee.org/)", source_tag_style))

    story.append(PageBreak())

    # ================= PAGE 4 =================
    story.append(Paragraph("Technical Societies, Publications & Standards", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#00629B'), spaceAfter=12))

    story.append(Paragraph("1. IEEE Technical Societies", h1_style))
    story.append(Paragraph(
        "IEEE is organized into 39 technical societies providing specialized literature, conferences, and certifications across disciplines:",
        body_style
    ))
    story.append(Paragraph("• <b>IEEE Computer Society (CS):</b> The premier membership organization for computer scientists and software engineers, publishing IEEE Transactions on Computers and IEEE Software.", bullet_style))
    story.append(Paragraph("• <b>IEEE Communications Society (ComSoc):</b> Focuses on wireless networks, optical communications, 5G/6G, and IoT communication protocols.", bullet_style))
    story.append(Paragraph("• <b>IEEE Power & Energy Society (PES):</b> Focuses on electric power generation, smart grids, renewable energy systems, and high-voltage distribution.", bullet_style))
    story.append(Paragraph("• <b>IEEE Robotics and Automation Society (RAS):</b> Leads research in autonomous vehicles, collaborative robotics, control theory, and robotic vision.", bullet_style))
    story.append(Paragraph("• <b>IEEE Signal Processing Society (SPS):</b> The world's first technical society, advancing audio processing, computer vision, and machine learning algorithms.", bullet_style))
    story.append(Paragraph("• <b>IEEE Engineering in Medicine and Biology Society (EMBS):</b> Advances biomedical devices, neural engineering, and healthcare informatics.", bullet_style))

    story.append(Paragraph("2. IEEE Xplore Digital Library", h1_style))
    story.append(Paragraph(
        "IEEE publishes roughly one-third of the world's literature in electrical engineering, computer science, and electronics. "
        "The IEEE Xplore Digital Library contains more than 6 million peer-reviewed articles, standards, and conference proceedings, "
        "averaging over 12 million downloads each month by researchers and institutions worldwide.",
        body_style
    ))

    story.append(Paragraph("3. IEEE Standards Association (IEEE-SA)", h1_style))
    story.append(Paragraph(
        "The IEEE Standards Association is a globally recognized standards-setting body. Its landmark standards shape modern computing, notably: "
        "<b>IEEE 802.3</b> defining Ethernet wired local area networks; <b>IEEE 802.11</b> defining Wi-Fi wireless local networking; "
        "<b>IEEE 754</b> governing floating-point arithmetic; and <b>IEEE 1588</b> for precision clock synchronization.",
        body_style
    ))
    story.append(Paragraph("Source: IEEE Standards Association & Publications Directory (https://standards.ieee.org/)", source_tag_style))

    doc.build(story)
    print(f"Sample IEEE PDF successfully created at: {output_path}")

if __name__ == "__main__":
    generate_ieee_pdf()
