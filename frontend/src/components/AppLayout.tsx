import {
  AppBar,
  Layout,
  LoadingIndicator,
  LocalesMenuButton,
  ToggleThemeButton,
  useLocales,
  useThemesContext,
} from "react-admin";
import type { AppBarProps, LayoutProps } from "react-admin";

import { NotificationCenterButton } from "./NotificationCenter";

function QueueManagerToolbar() {
  const locales = useLocales();
  const { darkTheme } = useThemesContext();

  return (
    <>
      <NotificationCenterButton />
      {locales && locales.length > 1 ? <LocalesMenuButton /> : null}
      {darkTheme ? <ToggleThemeButton /> : null}
      <LoadingIndicator />
    </>
  );
}

function QueueManagerAppBar(props: AppBarProps) {
  return <AppBar {...props} toolbar={<QueueManagerToolbar />} />;
}

export function AppLayout(props: LayoutProps) {
  return <Layout {...props} appBar={QueueManagerAppBar} />;
}
