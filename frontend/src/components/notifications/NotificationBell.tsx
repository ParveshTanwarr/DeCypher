import { Bell, CheckCircle2, X } from "lucide-react";
import { useEffect, useState } from "react";

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  time: string;
  type?: "info" | "success" | "warning";
  read?: boolean;
}

interface Props {
  notifications: AppNotification[];
  onMarkAllRead: () => void;
}

export default function NotificationBell({ notifications, onMarkAllRead }: Props) {
  const [open, setOpen] = useState(false);
  const unread = notifications.filter((item) => !item.read).length;

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!(event.target as HTMLElement).closest(".notification-wrap")) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <div className="notification-wrap">
      <button className="notification-button" aria-label="Notifications" onClick={() => setOpen((value) => !value)}>
        <Bell size={17} />
        {unread > 0 && <span className="notification-count">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="notification-panel">
          <div className="notification-header">
            <div><strong>Notifications</strong><small>{unread ? `${unread} unread` : "All caught up"}</small></div>
            {unread > 0 && <button onClick={onMarkAllRead}>Mark all read</button>}
            <button className="notification-close" aria-label="Close" onClick={() => setOpen(false)}><X size={14} /></button>
          </div>
          <div className="notification-list">
            {notifications.length === 0 ? (
              <div className="notification-empty"><CheckCircle2 size={20} /><span>No new notifications</span></div>
            ) : notifications.map((item) => (
              <div key={item.id} className={`notification-item ${item.read ? "read" : ""}`}>
                <span className={`notification-dot ${item.type || "info"}`} />
                <div><strong>{item.title}</strong><p>{item.message}</p><small>{item.time}</small></div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
