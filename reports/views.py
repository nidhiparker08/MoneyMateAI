from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
import io

from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch

from .services import ReportService
from .models import ReportHistory


@login_required
def reports_page(request):
    last_report = (
        ReportHistory.objects
        .filter(user=request.user)
        .order_by("-generated_at")
        .first()
    )

    total_downloads = (
        ReportHistory.objects
        .filter(user=request.user)
        .count()
    )

    context = {

        "active_page": "reports",

        "last_report": (
            last_report.generated_at.strftime("%d %b %Y")
            if last_report
            else "--"
        ),

        "total_downloads": total_downloads,

        "report_cards": [

            {
                "title": "Weekly Report",
                "description": "Download the last 7 days financial report.",
                "icon": "fa-calendar-week",
                "period": "weekly",
            },

            {
                "title": "Monthly Report",
                "description": "Complete monthly income and expense summary.",
                "icon": "fa-calendar",
                "period": "monthly",
            },

            {
                "title": "Quarterly Report",
                "description": "Financial report for the previous quarter.",
                "icon": "fa-chart-column",
                "period": "quarterly",
            },

            {
                "title": "Half-Yearly Report",
                "description": "Six months financial analysis.",
                "icon": "fa-chart-line",
                "period": "halfyear",
            },

            {
                "title": "Previous Year Report",
                "description": "Yearly financial statement.",
                "icon": "fa-file-lines",
                "period": "year",
            },

            {
                "title": "Custom Report",
                "description": "Choose your own date range.",
                "icon": "fa-sliders",
                "period": "custom",
            },

        ]

    }

    return render(
        request,
        "reports/reports.html",
        context,
    )


@login_required
def download_report(request):

    period = request.GET.get("period", "monthly")

    start = request.GET.get("start")

    end = request.GET.get("end")

    try:

        if period == "custom":

            start_date = datetime.strptime(
                start,
                "%Y-%m-%d"
            ).date()

            end_date = datetime.strptime(
                end,
                "%Y-%m-%d"
            ).date()

        else:

            start_date = None

            end_date = None

        response = ReportService.generate_pdf(

            request.user,

            period,

            start_date,

            end_date,

        )

        ReportHistory.objects.create(

            user=request.user,

            report_type=period,

        )

        return response

    except Exception as e:

        raise e
    
    # ==========================================================
    # GENERATE PDF
    # ==========================================================

    @staticmethod
    def generate_pdf(

        user,

        report_type,

        start_date=None,

        end_date=None,

    ):

        start, end = ReportService.get_dates(

            report_type,

            start_date,

            end_date,

        )

        transactions = ReportService.get_transactions(

            user,

            start,

            end,

        )

        summary = ReportService.get_summary(

            transactions,

        )

        categories = ReportService.get_categories(

            transactions,

        )

        buffer = io.BytesIO()

        document = ReportService.create_document(

            buffer,

        )

        title_style, heading, normal = ReportService.get_styles()

        story = []

        # HEADER

        ReportService.add_header(

            story,

            title_style,

            heading,

            user,

            report_type,

            start,

            end,

        )

        # SUMMARY

        ReportService.add_summary(

            story,

            heading,

            summary,

        )

        # CATEGORY TABLE

        ReportService.add_category_table(

            story,

            heading,

            categories,

        )

        # =====================================================
        # TRANSACTIONS
        # =====================================================

        story.append(

            Paragraph(

                "<b>Transactions</b>",

                heading,

            )

        )

        rows = [

            [

                "Date",

                "Title",

                "Category",

                "Type",

                "Amount",

            ]

        ]

        for t in transactions:

            rows.append(

                [

                    t.transaction_date.strftime(

                        "%d-%m-%Y"

                    ),

                    t.title,

                    t.category.name if t.category else "-",

                    t.transaction_type.title(),

                    f"₹ {t.amount}",

                ]

            )

        if len(rows) == 1:

            rows.append(

                [

                    "-",

                    "No Transactions",

                    "-",

                    "-",

                    "-",

                ]

            )

        table = Table(

            rows,

            colWidths=[70,130,90,60,80],

        )

        table.setStyle(

            TableStyle(

                [

                    ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#8B5CF6")),

                    ("TEXTCOLOR",(0,0),(-1,0),colors.white),

                    ("GRID",(0,0),(-1,-1),0.5,colors.grey),

                    ("BACKGROUND",(0,1),(-1,-1),colors.beige),

                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

                    ("FONTSIZE",(0,0),(-1,-1),9),

                ]

            )

        )

        story.append(table)

        story.append(

            Spacer(

                1,

                .30 * inch,

            )

        )

        story.append(

            Paragraph(

                "<b>Generated by MoneyMate</b>",

                normal,

            )

        )

        document.build(

            story

        )

        pdf = buffer.getvalue()

        buffer.close()

        response = HttpResponse(

            pdf,

            content_type="application/pdf",

        )

        response["Content-Disposition"] = (

            f'attachment; filename="{report_type}_report.pdf"'

        )

        return response