import { Box } from "@mui/material";
import { useRecordContext } from "react-admin";

type JsonFieldProps = {
  source: string;
};

export function JsonField({ source }: JsonFieldProps) {
  const record = useRecordContext<Record<string, unknown>>();
  const value = record?.[source];

  return (
    <Box
      component="pre"
      sx={{
        bgcolor: (theme) => (theme.palette.mode === "dark" ? "grey.900" : "grey.100"),
        border: 1,
        borderColor: "divider",
        borderRadius: 1,
        color: "text.primary",
        fontFamily: "monospace",
        fontSize: 13,
        m: 0,
        maxWidth: "100%",
        overflow: "auto",
        p: 2,
        whiteSpace: "pre-wrap",
      }}
    >
      {JSON.stringify(value ?? null, null, 2)}
    </Box>
  );
}
