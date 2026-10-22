"""Service — central de notificações do usuário."""

from __future__ import annotations

from pymysql.connections import Connection

from ..models import Notification


class NotificationService:
    @staticmethod
    def list_user_notifications(conn: Connection, user_id: int) -> dict:
        notifications = Notification.find_by_user(conn, user_id)
        unread = Notification.count_unread(conn, user_id)
        for n in notifications:
            n["created_at"] = str(n["created_at"])
            n["is_read"] = bool(n["is_read"])
        return {
            "unread_count": unread,
            "notifications": notifications,
        }

    @staticmethod
    def mark_read(conn: Connection, notification_id: int, user_id: int) -> dict:
        success = Notification.mark_as_read(conn, notification_id, user_id)
        conn.commit()
        return {"success": success}

    @staticmethod
    def mark_all_read(conn: Connection, user_id: int) -> dict:
        count = Notification.mark_all_as_read(conn, user_id)
        conn.commit()
        return {"marked_count": count}
