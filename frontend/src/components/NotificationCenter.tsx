import NotificationsIcon from "@mui/icons-material/Notifications";
import {
  Badge,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  List as MuiList,
  ListItem,
  ListItemText,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

type AppNotification = {
  id: number;
  message: string;
  createdAt: Date;
};

type AddNotification = (notification: Pick<AppNotification, "message">) => void;

type NotificationCenterContextValue = {
  addNotification: AddNotification;
  clearNotifications: () => void;
  notifications: AppNotification[];
};

const NotificationCenterContext = createContext<NotificationCenterContextValue | null>(null);

let nextNotificationId = 1;

export function NotificationCenterProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);

  const addNotification = useCallback<AddNotification>(({ message }) => {
    const notification = {
      id: nextNotificationId,
      message,
      createdAt: new Date(),
    };

    nextNotificationId += 1;
    setNotifications((current) => [notification, ...current].slice(0, 50));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const value = useMemo(
    () => ({ addNotification, clearNotifications, notifications }),
    [addNotification, clearNotifications, notifications],
  );

  return <NotificationCenterContext.Provider value={value}>{children}</NotificationCenterContext.Provider>;
}

export function NotificationCenterButton() {
  const { clearNotifications, notifications } = useNotificationCenter();
  const [open, setOpen] = useState(false);

  return (
    <>
      <Tooltip title="Notifications">
        <IconButton color="inherit" onClick={() => setOpen(true)} aria-label="Notifications">
          <Badge badgeContent={notifications.length} color="primary" max={99}>
            <NotificationsIcon />
          </Badge>
        </IconButton>
      </Tooltip>
      <Drawer anchor="right" open={open} onClose={() => setOpen(false)}>
        <Box sx={{ width: 360, maxWidth: "100vw" }} role="presentation">
          <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2} sx={{ p: 2 }}>
            <Typography variant="h6">Notifications</Typography>
            <Button size="small" onClick={clearNotifications} disabled={notifications.length === 0}>
              Clear
            </Button>
          </Stack>
          <Divider />
          {notifications.length === 0 ? (
            <Typography color="text.secondary" sx={{ p: 2 }}>
              No notifications
            </Typography>
          ) : (
            <MuiList disablePadding>
              {notifications.map((notification) => (
                <ListItem key={notification.id} divider alignItems="flex-start">
                  <ListItemText
                    primary={notification.message}
                    secondary={notification.createdAt.toLocaleTimeString()}
                    primaryTypographyProps={{ variant: "body2" }}
                    secondaryTypographyProps={{ variant: "caption" }}
                  />
                </ListItem>
              ))}
            </MuiList>
          )}
        </Box>
      </Drawer>
    </>
  );
}

export function useNotificationCenter() {
  const context = useContext(NotificationCenterContext);

  if (!context) {
    throw new Error("useNotificationCenter must be used within NotificationCenterProvider");
  }

  return context;
}
