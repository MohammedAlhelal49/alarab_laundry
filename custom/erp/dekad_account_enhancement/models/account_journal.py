# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo.exceptions import UserError
from odoo import _, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    sequence_date_format = fields.Selection(
        [
            ("none", "No Date"),
            ("year", "Year Only"),
            ("year_month", "Year and Month"),
        ],
        string="Sequence Date Format",
        default="year_month",
    )

    @staticmethod
    def _parse_name(name):
        """
        Split a sequence name into (pure_prefix, seq_str).
        Removes year/month from the prefix.
        """
        if not name:
            return "", "00001"

        segments = name.split("/")

        seq = None
        seq_idx = None

        for i in range(len(segments) - 1, -1, -1):
            if segments[i].isdigit():
                seq = segments[i]
                seq_idx = i
                break

        if seq is None:
            return name, "00001"

        prefix = [
            s for s in segments[:seq_idx]
            if not (s.isdigit() and len(s) in (2, 4))
        ]

        return "/".join(prefix), seq

    def action_resequence_journal(self):
        self.ensure_one()

        date_format = self.sequence_date_format

        moves = self.env["account.move"].search([
            ("journal_id", "=", self.id),
            ("state", "=", "posted"),
            ("name", "!=", "/"),
            ("name", "!=", False),
        ])

        if not moves:
            raise UserError(_("No posted journal entries found to resequence."))

        self.env.cr.execute("""
            SELECT id, name, date
            FROM account_move
            WHERE id = ANY(%s)
        """, (moves.ids,))

        rows = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}

        new_names = {}
        seen = set()
        need_resequence = False

        for move_id, (name, move_date) in rows.items():
            prefix, seq = self._parse_name(name)

            parts = []

            if prefix:
                parts.append(prefix)

            if date_format in ("year", "year_month"):
                parts.append(str(move_date.year))

            if date_format == "year_month":
                parts.append(f"{move_date.month:02d}")

            parts.append(seq)

            new_name = "/".join(parts)

            if new_name in seen:
                need_resequence = True

            seen.add(new_name)
            new_names[move_id] = new_name

        if need_resequence:
            grouped = defaultdict(list)

            for move_id, (name, move_date) in rows.items():
                prefix, seq_str = self._parse_name(name)

                key = (prefix,)

                if date_format == "year":
                    key += (move_date.year,)

                elif date_format == "year_month":
                    key += (move_date.year, move_date.month)

                grouped[key].append((move_id, move_date))

            new_names = {}

            for key, records in grouped.items():
                records.sort(key=lambda r: (r[1], r[0]))

                for seq, (move_id, move_date) in enumerate(records, start=1):
                    number = str(seq).zfill(5)

                    parts = [str(x) for x in key if x]
                    parts.append(number)

                    new_names[move_id] = "/".join(parts)

        moves_to_update = self.env["account.move"].browse(new_names.keys())

        moves_to_update.write({"name": False})
        self.env.cr.flush()

        for move in moves_to_update:
            new_name = new_names[move.id]

            prefix = (
                new_name.rsplit("/", 1)[0] + "/"
                if "/" in new_name else ""
            )

            move.with_context(check_move_validity=False).write({
                "name": new_name,
                "sequence_prefix": prefix,
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Resequence Complete"),
                "message": _(
                    "%s journal entries have been resequenced."
                ) % len(new_names),
                "type": "success",
                "sticky": False,
            },
        }