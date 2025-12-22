// App.tsx
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import MapScreen from './screens/MapScreen';
import ResultsScreen from './screens/ResultsScreen';
import CropSelectionScreen from './screens/CropSelectionScreen';

export type RootStackParamList = {
  Home: undefined;
  Map: undefined;
  Results: undefined;
  CropSelection: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ headerTitle: 'Farm Plot Mapper' }}
        />
        <Stack.Screen
          name="Map"
          component={MapScreen}
          options={{ headerTitle: 'Draw Your Plot' }}
        />
        <Stack.Screen
          name="Results"
          component={ResultsScreen}
          options={{ headerTitle: 'Analysis Results' }} />
        <Stack.Screen name="CropSelection" component={CropSelectionScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}