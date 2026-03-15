/**
 * Index route — redirects to the tab navigator.
 *
 * Expo Router needs a file at app/index.tsx as the root route.
 * This redirects to the care tab (main landing screen).
 */
import { Redirect } from "expo-router";

export default function Index() {
    return <Redirect href="/(tabs)/care" />;
}
