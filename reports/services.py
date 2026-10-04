from datetime import date, timedelta
from decimal import Decimal
import locale

from django.db.models import Sum
from django.db.models.functions import Coalesce

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from reportlab.platypus import HRFlowable

from transactions.models import Transaction
import io
from django.http import HttpResponse

import os
import tempfile

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from reportlab.platypus import Image

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class ReportService:

    @staticmethod
    def get_dates(report_type, start_date=None, end_date=None):

        today = date.today()

        if report_type == "weekly":

            start = today - timedelta(days=6)
            end = today

        elif report_type == "monthly":

            start = today.replace(day=1)
            end = today

        elif report_type == "quarterly":

            q = (today.month - 1) // 3

            start = date(
                today.year,
                q * 3 + 1,
                1,
            )

            end = today

        elif report_type == "halfyear":

            if today.month <= 6:

                start = date(today.year, 1, 1)

            else:

                start = date(today.year, 7, 1)

            end = today

        elif report_type == "year":

            start = date(today.year, 1, 1)
            end = today

        else:

            start = start_date
            end = end_date

        return start, end

    @staticmethod
    def get_transactions(user, start, end):

        return (

            Transaction.objects

            .filter(

                user=user,

                transaction_date__range=[

                    start,
                    end,

                ]

            )

            .select_related("category")

            .order_by("-transaction_date")

        )

    @staticmethod
    def get_summary(transactions):

        # ==========================
        # TOTAL INCOME
        # ==========================

        income = (

            transactions

            .filter(

                transaction_type="income"

            )

            .aggregate(

                total=Coalesce(

                    Sum("amount"),

                    Decimal("0")

                )

            )["total"]

        )

        # ==========================
        # TOTAL EXPENSE
        # ==========================

        expense = (

            transactions

            .filter(

                transaction_type="expense"

            )

            .aggregate(

                total=Coalesce(

                    Sum("amount"),

                    Decimal("0")

                )

            )["total"]

        )

        # ==========================
        # BALANCE
        # ==========================

        balance = income - expense

        # ==========================
        # TOTAL TRANSACTIONS
        # ==========================

        transaction_count = transactions.count()

        # ==========================
        # UNIQUE EXPENSE CATEGORIES
        # ==========================

        category_count = (

            transactions

            .filter(

                transaction_type="expense"

            )

            .values("category")

            .distinct()

            .count()

        )

        # ==========================
        # AVERAGE TRANSACTION VALUE
        # ==========================

        if transaction_count > 0:

            average_transaction = (

                expense / Decimal(transaction_count)

            )

        else:

            average_transaction = Decimal("0")

        # ==========================
        # LARGEST EXPENSE
        # ==========================

        largest_transaction = (

            transactions

            .filter(

                transaction_type="expense"

            )

            .order_by("-amount")

            .first()

        )

        if largest_transaction:

            largest_expense = largest_transaction.amount

        else:

            largest_expense = Decimal("0")

        # ==========================
        # RETURN DATA
        # ==========================

        return {

            "income": income,

            "expense": expense,

            "balance": balance,

            "transactions": transaction_count,

            "categories": category_count,

            "average": average_transaction,

            "largest": largest_expense,

        }

    @staticmethod
    def get_categories(transactions):

        return (

            transactions

            .filter(

                transaction_type="expense"

            )

            .values(

                "category__name"

            )

            .annotate(

                total=Sum("amount")

            )

            .order_by("-total")

        )

    @staticmethod
    def create_document(response):

        return SimpleDocTemplate(

            response,

            rightMargin=30,

            leftMargin=30,

            topMargin=30,

            bottomMargin=30,

        )

    @staticmethod
    def get_styles():

        styles = getSampleStyleSheet()

        title = styles["Heading1"]

        title.alignment = TA_CENTER

        heading = styles["Heading2"]

        normal = styles["BodyText"]

        return title, heading, normal

    @staticmethod
    def format_currency(amount):

        try:

            amount = float(amount)

        except Exception:

            amount = 0

        amount = f"{amount:,.2f}"

        integer, decimal = amount.split(".")

        integer = integer.replace(",", "")

        if len(integer) > 3:

            last3 = integer[-3:]

            rest = integer[:-3]

            parts = []

            while len(rest) > 2:

                parts.insert(0, rest[-2:])

                rest = rest[:-2]

            if rest:

                parts.insert(0, rest)

            integer = ",".join(parts) + "," + last3

        return f"₹{integer}.{decimal}"

    @staticmethod
    def add_header(
        story,
        title_style,
        heading,
        user,
        report_type,
        start,
        end,
    ):

        # ===========================
        # APP TITLE
        # ===========================


        logo_path = os.path.join(
            "static",
            "images",
            "favicon.png",
        )

        logo = Image(
            logo_path,
            width=40,
            height=40,
        )

        title = Paragraph(
            """
            <para align="center">
            <font size="22" color="white">
            <b>MoneyMate</b>
            </font>
            <br/>
            <font size="11" color="white">
            AI Powered Personal Finance Report
            </font>
            </para>
            """,
            title_style,
        )

        title_table = Table(
            [
                [logo, title]
            ],
            colWidths=[55, 425],
        )

        title_table.setStyle(

            TableStyle(

                [

                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#7C3AED")),

                    ("BOTTOMPADDING", (0, 0), (-1, -1), 18),

                    ("TOPPADDING", (0, 0), (-1, -1), 18),

                    ("BOX", (0, 0), (-1, -1), 0, colors.white),

                ]

            )

        )

        story.append(title_table)

        story.append(Spacer(1, 0.35 * inch))

        # ===========================
        # REPORT INFORMATION
        # ===========================

        info = [

            ["Prepared For", user.username],

            ["Report Type", report_type.title()],

            ["Report Period",
             f"{start.strftime('%d %b %Y')}  →  {end.strftime('%d %b %Y')}"],

            ["Report ID",
             f"FIN-{date.today().strftime('%Y%m%d')}-{user.id:04d}",
            ],

            ["Generated On",
             date.today().strftime("%d %b %Y")],

        ]

        info_table = Table(

            info,

            colWidths=[140, 340],

        )

        info_table.setStyle(

            TableStyle(

                [

                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#8B5CF6")),

                    ("TEXTCOLOR", (0, 0), (0, -1), colors.white),

                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),

                    ("BACKGROUND", (1, 0), (1, -1), colors.whitesmoke),

                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),

                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),

                    ("TOPPADDING", (0, 0), (-1, -1), 8),

                    ("LEFTPADDING", (0, 0), (-1, -1), 10),

                ]

            )

        )

        story.append(info_table)

        story.append(Spacer(1, 0.35 * inch))

    # ==========================================================
    # SUMMARY SECTION
    # ==========================================================

    @staticmethod
    def add_summary(

        story,

        heading,

        normal,

        summary,

    ):

        # ======================================
        # SECTION TITLE
        # ======================================

        story.append(

            Paragraph(

                "<font size=18><b>Financial Dashboard</b></font>",

                heading,

            )

        )

        story.append(

            Spacer(

                1,

                .20 * inch,

            )

        )

        # ======================================
        # KPI DATA
        # ======================================

        row1 = [

            [

                Paragraph(

                    f"<b>Income</b><br/><br/>{ReportService.format_currency(summary['income'])}",

                    normal,

                ),

                Paragraph(

                    f"<b>Expense</b><br/><br/>{ReportService.format_currency(summary['expense'])}",

                    normal,

                ),

                Paragraph(

                    f"<b>Balance</b><br/><br/>{ReportService.format_currency(summary['balance'])}",

                    normal,

                ),

            ]

        ]

        row2 = [

            [

                Paragraph(

                    f"<b>Transactions</b><br/><br/>{summary['transactions']}",

                    normal,

                ),

                Paragraph(

                    f"<b>Categories</b><br/><br/>{summary['categories']}",

                    normal,

                ),

                Paragraph(

                    f"<b>Average Expense</b><br/><br/>{ReportService.format_currency(summary['average'])}",

                    normal,

                ),

            ]

        ]

        top = Table(

            row1,

            colWidths=[160,160,160],

            rowHeights=[80],

        )

        bottom = Table(

            row2,

            colWidths=[160,160,160],

            rowHeights=[80],

        )

        card_style = TableStyle([

            ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F8F5FF")),

            ("BOX",(0,0),(-1,-1),1.5,colors.HexColor("#8B5CF6")),

            ("INNERGRID",(0,0),(-1,-1),0.5,colors.HexColor("#E9D8FD")),

            ("TOPPADDING",(0,0),(-1,-1),18),

            ("BOTTOMPADDING",(0,0),(-1,-1),18),

            ("LEFTPADDING",(0,0),(-1,-1),20),

            ("RIGHTPADDING",(0,0),(-1,-1),20),

            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),

        ])

        top.setStyle(card_style)

        bottom.setStyle(card_style)

        story.append(top)

        story.append(

            Spacer(

                1,

                .15 * inch,

            )

        )

        story.append(bottom)

        story.append(

            Spacer(

                1,

                .30 * inch,

            )

        )

    # ==========================================================
    # CATEGORY TABLE
    # ==========================================================

    @staticmethod
    def add_category_table(

        story,

        heading,

        categories,

    ):

        story.append(

            Paragraph(

                "<b>Expense by Category</b>",

                heading,

            )

        )

        story.append(

            Spacer(

                1,

                .10 * inch,

            )

        )

        # ==========================================
        # CALCULATE TOTAL EXPENSE
        # ==========================================

        total_expense = sum(

            float(category["total"])

            for category in categories

        )

        # ==========================================
        # TABLE HEADER
        # ==========================================

        rows = [

            [

                "Category",

                "Amount",

                "%",

            ]

        ]

        # ==========================================
        # TABLE DATA
        # ==========================================

        for category in categories:

            amount = float(category["total"])

            percentage = (

                (amount / total_expense) * 100

                if total_expense > 0

                else 0

            )

            rows.append(

                [

                    category["category__name"] or "Uncategorized",

                    ReportService.format_currency(

                        category["total"]

                    ),

                    f"{percentage:.1f}%",

                ]

            )

        # ==========================================
        # EMPTY STATE
        # ==========================================

        if len(rows) == 1:

            rows.append(

                [

                    "No Expense",

                    "₹0.00",

                    "0%",

                ]

            )

        # ==========================================
        # CREATE TABLE
        # ==========================================

        table = Table(

            rows,

            colWidths=[210,150,70],

        )

        style = TableStyle(

            [

                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#8B5CF6")),

                ("TEXTCOLOR",(0,0),(-1,0),colors.white),

                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

                ("FONTSIZE",(0,0),(-1,0),11),

                ("BOTTOMPADDING",(0,0),(-1,0),10),

                ("TOPPADDING",(0,0),(-1,0),10),

                ("GRID",(0,0),(-1,-1),0.4,colors.grey),

            ]

        )

        # ==========================================
        # ZEBRA STRIPES
        # ==========================================

        for row in range(1, len(rows)):

            if row % 2 == 0:

                bg = colors.HexColor("#F8F5FF")

            else:

                bg = colors.HexColor("#FFFDF4")

            style.add(

                "BACKGROUND",

                (0,row),

                (-1,row),

                bg,

            )

        table.setStyle(style)

        story.append(table)

        story.append(

            Spacer(

                1,

                .30 * inch,

            )

        )

    @staticmethod
    def add_category_chart(story, heading, categories):

        if not categories:
            return

        labels = []
        values = []

        for item in categories:

            labels.append(

                item["category__name"] or "Other"

            )

            values.append(

                float(item["total"])

            )

        plt.figure(

            figsize=(6,6),

            facecolor="white",

        )

        colors = [
            "#8B5CF6",
            "#A78BFA",
            "#C4B5FD",
            "#DDD6FE",
            "#7C3AED",
            "#6D28D9",
        ]

        wedges, texts, autotexts = plt.pie(

            values,

            labels=None,

            autopct="%1.1f%%",

            startangle=90,

            colors=colors,

            wedgeprops={

                "linewidth":1,

                "edgecolor":"white",

            },

        )

        plt.legend(

            wedges,

            labels,

            title="Categories",

            loc="center left",

            bbox_to_anchor=(1,0.5),

        )

        plt.title(

            "Expense Distribution",

            fontsize=16,

            fontweight="bold",

        )

        temp = tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        )

        plt.savefig(
            temp.name,
            dpi=220,
            bbox_inches="tight",
        )

        plt.close()

        story.append(
            Paragraph(
                "<b>Expense Distribution</b>",
                heading,
            )
        )

        story.append(
            Image(
                temp.name,
                width=260,
                height=260,
            )
        )

        story.append(
            Spacer(
                1,
                0.25 * inch,
            )
        )

        #os.unlink(temp.name)

    @staticmethod
    def add_page_footer(canvas, doc):


        logo_path = os.path.join(
            "static",
            "images",
            "favicon.png",
        )

        canvas.saveState()

        width = doc.pagesize[0]
        height = doc.pagesize[1]

        # ==========================================
        # TOP FOOTER LINE
        # ==========================================

        canvas.setStrokeColor(colors.HexColor("#8B5CF6"))
        canvas.setLineWidth(1)

        canvas.line(

            30,

            35,

            width - 30,

            35,

        )

        # ==========================================
        # LEFT TEXT
        # ==========================================

        canvas.setFont(

            "Helvetica-Bold",

            9,

        )

        if os.path.exists(logo_path):

            canvas.drawImage(

                logo_path,

                32,

                6,

                width=18,

                height=18,

                preserveAspectRatio=True,

                mask="auto",

            )

        canvas.setFont(
            "Helvetica-Bold",
            9,
        )

        canvas.drawString(
            56,
            20,
            "MoneyMate",
        )

        canvas.setFont(

            "Helvetica",

            8,

        )

        canvas.drawString(

            35,

            9,

            "AI Powered Personal Finance Platform",

        )

        # ==========================================
        # RIGHT TEXT
        # ==========================================

        canvas.drawRightString(

            width - 35,

            20,

            f"Generated: {date.today().strftime('%d %b %Y')}",

        )

        canvas.drawRightString(

            width - 35,

            9,

            f"Confidential  |  Page {doc.page}",

        )

        canvas.restoreState()

    @staticmethod
    def generate_pdf(
        user,
        report_type,
        start_date=None,
        end_date=None,
    ):


        font_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "static",
            "fonts",
            "DejaVuSans.ttf",
        )

        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("DejaVu", font_path))
            base_font = "DejaVu"
        else:
            base_font = "Helvetica"

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

        from io import BytesIO

        buffer = BytesIO()

        document = ReportService.create_document(
            buffer,
        )

        title_style, heading, normal = ReportService.get_styles()

        story = []

        ReportService.add_header(
            story,
            title_style,
            heading,
            user,
            report_type,
            start,
            end,
        )

        ReportService.add_summary(
            story,
            heading,
            normal,
            summary,
        )

        ReportService.add_category_table(
            story,
            heading,
            categories,
        )

        ReportService.add_category_chart(
            story,
            heading,
            categories,
        )

        story.append(
            Paragraph(
                "<b>Transactions</b>",
                heading,
            )
        )

        rows = [[
            "Date",
            "Title",
            "Category",
            "Type",
            "Amount",
        ]]

        for transaction in transactions:

            rows.append([
                transaction.transaction_date.strftime("%d-%m-%Y"),
                transaction.title,
                transaction.category.name if transaction.category else "-",
                transaction.transaction_type.title(),
                ReportService.format_currency(transaction.amount),
            ])

        if len(rows) == 1:

            rows.append([
                "-",
                "No Transactions",
                "-",
                "-",
                "-",
            ])

        table = Table(
            rows,
            colWidths=[70, 150, 100, 70, 80],
        )

        table.setStyle(

            TableStyle([

                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8B5CF6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),

            ])

        )

        story.append(table)

        story.append(
            Spacer(
                1,
                .25 * inch,
            )
        )

        document.build(

            story,

            onFirstPage=ReportService.add_page_footer,

            onLaterPages=ReportService.add_page_footer,

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