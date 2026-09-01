import { GraphNode, GraphLink, ActorProfile, GraphData } from '../types/graph';

export const MOCK_NODES: GraphNode[] = [
  // ACTORS
  {
    id: 'A00001',
    category: 'ACTOR',
    label: 'A00001',
    subLabel: 'Cluster A00001',
    risk: 'critical',
    confidence: 0.92,
    clusterId: 'Cluster A00001',
    signals: ['Wallet reuse', 'Stylometry', 'Handle correlation', 'Dormancy-Rebrand cycle'],
    val: 28,
  },
  {
    id: 'A00042',
    category: 'ACTOR',
    label: 'A00042',
    subLabel: 'Cluster A00042',
    risk: 'high',
    confidence: 0.84,
    clusterId: 'Cluster A00042',
    signals: ['Shared ETH wallet', 'Exploit exchange presence', 'PGP key fingerprint match'],
    val: 24,
  },
  {
    id: 'A00118',
    category: 'ACTOR',
    label: 'A00118',
    subLabel: 'Cluster A00118',
    risk: 'medium',
    confidence: 0.71,
    clusterId: 'Cluster A00118',
    signals: ['Sparse darknet activity', 'Static BTC treasury'],
    val: 20,
  },

  // HANDLES
  {
    id: 'H00001',
    category: 'HANDLE',
    label: 'nyxinhex99',
    subLabel: 'Marketplace / Forum',
    confidence: 0.88,
    platform: 'Dark Market / Forum',
    actorId: 'A00001',
    val: 16,
  },
  {
    id: 'H00002',
    category: 'HANDLE',
    label: 'vexatrace',
    subLabel: 'Telegram / P2P',
    confidence: 0.81,
    platform: 'Telegram / P2P Channels',
    actorId: 'A00001',
    val: 16,
  },
  {
    id: 'H00073',
    category: 'HANDLE',
    label: 'circuitmoth',
    subLabel: 'Exploit Exchange',
    confidence: 0.77,
    platform: '0-day / Exploit Broker',
    actorId: 'A00042',
    val: 15,
  },
  {
    id: 'H00194',
    category: 'HANDLE',
    label: 'quietledger',
    subLabel: 'Darknet Directory',
    confidence: 0.69,
    platform: 'Tor Vendor Index',
    actorId: 'A00118',
    val: 14,
  },

  // WALLETS
  {
    id: 'W-XMR-01',
    category: 'WALLET',
    label: 'XMR · 4b5U...aoX',
    subLabel: 'Monero Primary Deposit',
    confidence: 0.94,
    currency: 'XMR',
    address: '4b5U...aoX',
    fullAddress: '4b5U89XqLm9WjS73kL2w8PzQnm6V1RtyE9qZ8a82aoX',
    val: 12,
  },
  {
    id: 'W-ETH-02',
    category: 'WALLET',
    label: 'ETH · 0x7e...870',
    subLabel: 'Ethereum Smart Contract / Cashout',
    confidence: 0.82,
    currency: 'ETH',
    address: '0x7e...870',
    fullAddress: '0x7e44a193910F79bA3543164929828d1D35a870',
    val: 12,
  },
  {
    id: 'W-BTC-03',
    category: 'WALLET',
    label: 'BTC · bc1q...9pz',
    subLabel: 'Bitcoin Cold Storage',
    confidence: 0.74,
    currency: 'BTC',
    address: 'bc1q...9pz',
    fullAddress: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjh4729pz',
    val: 12,
  },
];

export const MOCK_LINKS: GraphLink[] = [
  {
    id: 'l1',
    source: 'A00001',
    target: 'H00001',
    type: 'controls',
    confidence: 0.92,
    notes: 'Direct session token correlation & authorial stylometry similarity 94.2%',
  },
  {
    id: 'l2',
    source: 'A00001',
    target: 'H00002',
    type: 'controls',
    confidence: 0.86,
    notes: 'Rebrand lineage observed following 78-day dormancy period',
  },
  {
    id: 'l3',
    source: 'A00042',
    target: 'H00073',
    type: 'controls',
    confidence: 0.84,
    notes: 'PGP key signature reuse across Russian-language exploit hub',
  },
  {
    id: 'l4',
    source: 'A00118',
    target: 'H00194',
    type: 'controls',
    confidence: 0.71,
    notes: 'Recurring Tor exit node routing and timing profile correlation',
  },
  {
    id: 'l5',
    source: 'H00001',
    target: 'W-XMR-01',
    type: 'uses wallet',
    confidence: 0.94,
    notes: 'Explicit escrow payout target published in 14 verified forum listings',
  },
  {
    id: 'l6',
    source: 'H00002',
    target: 'W-ETH-02',
    type: 'uses wallet',
    confidence: 0.82,
    notes: 'P2P transaction broadcast linked to Telegram bot checkout mechanism',
  },
  {
    id: 'l7',
    source: 'H00073',
    target: 'W-ETH-02',
    type: 'wallet reuse',
    confidence: 0.79,
    notes: 'Direct fund routing through shared Ethereum deposit contract',
  },
  {
    id: 'l8',
    source: 'H00194',
    target: 'W-BTC-03',
    type: 'uses wallet',
    confidence: 0.74,
    notes: 'Static donation address embedded in vendor profile signature',
  },
  {
    id: 'l9',
    source: 'A00001',
    target: 'A00042',
    type: 'shared wallet signal',
    confidence: 0.63,
    notes: 'Indirect financial infrastructure convergence through ETH address 0x7e...870',
  },
];

export const MOCK_ACTORS_DATA: Record<string, ActorProfile> = {
  A00001: {
    id: 'A00001',
    clusterId: 'Cluster A00001',
    name: 'Threat Cluster A00001',
    risk: 'critical',
    confidence: 0.92,
    threatCategory: 'Initial Access Broker / Ransomware Affiliate Infrastructure',
    firstSeen: '2023-02-20',
    lastActive: '2025-02-18 (Active)',
    summary: 'High-tier cybercrime cluster operating illicit marketplace channels, cryptocurrency laundering circuits, and rebranding operations.',
    handles: ['nyxinhex99', 'vexatrace'],
    wallets: [
      {
        currency: 'XMR',
        address: '4b5U...aoX',
        fullAddress: '4b5U89XqLm9WjS73kL2w8PzQnm6V1RtyE9qZ8a82aoX',
        role: 'Primary Monero Liquidity & Darknet Escrow',
      },
      {
        currency: 'ETH',
        address: '0x7e...870',
        fullAddress: '0x7e44a193910F79bA3543164929828d1D35a870',
        role: 'Secondary Off-Ramp via Shared Smart Contract',
      },
    ],
    signals: [
      {
        id: 'sig-1',
        title: 'HANDLE CORRELATION',
        type: 'HANDLE CORRELATION',
        description: 'nyxinhex99 → vexatrace',
        confidence: 0.86,
        severity: 'critical',
        details: 'Sequential handle adoption with identical cryptographic signing patterns and consistent vocabulary fingerprint.',
      },
      {
        id: 'sig-2',
        title: 'WALLET REUSE',
        type: 'WALLET REUSE',
        description: 'XMR wallet 4b5U...aoX',
        confidence: 0.94,
        severity: 'critical',
        details: '14 confirmed marketplace payouts routing to identical privacy-preserving vault address.',
      },
      {
        id: 'sig-3',
        title: 'BEHAVIORAL SIGNAL',
        type: 'BEHAVIORAL SIGNAL',
        description: 'Stylometric similarity (91.4%)',
        confidence: 0.91,
        severity: 'high',
        details: 'Cross-platform NLP stylometry matches punctuation habits, Cyrillic keyboard slips, and markdown syntax structure.',
      },
      {
        id: 'sig-4',
        title: 'LIFECYCLE SIGNAL',
        type: 'LIFECYCLE SIGNAL',
        description: 'Possible rebrand after dormancy',
        confidence: 0.86,
        severity: 'high',
        details: '78-day dormancy gap on primary handle nyxinhex99 was immediately succeeded by vexatrace emergence on Telegram.',
      },
      {
        id: 'sig-5',
        title: 'INFRASTRUCTURE OVERLAP',
        type: 'INFRASTRUCTURE',
        description: 'Shared ETH deposit proxy with Cluster A00042',
        confidence: 0.63,
        severity: 'medium',
        details: 'Financial hop to Ethereum address 0x7e...870 establishes indirect collusion or shared money-mule broker.',
      },
    ],
    timeline: [
      {
        id: 't-1',
        date: '2023-02-20',
        title: 'FIRST HANDLE OBSERVED',
        description: 'Handle nyxinhex99 appears in marketplace activity advertising access credentials and bespoke loader payloads.',
        confidence: 0.88,
        type: 'OBSERVED',
      },
      {
        id: 't-2',
        date: '2024-03-17',
        title: 'DORMANCY SIGNAL',
        description: 'Primary handle stops posting while related wallet activity continues on Monero blockchain.',
        confidence: 0.76,
        type: 'DORMANCY',
      },
      {
        id: 't-3',
        date: '2024-06-01',
        title: 'LIKELY REBRAND',
        description: 'New handle vexatrace appears with matching wallet and stylistic signals across Telegram underground channels.',
        confidence: 0.86,
        type: 'REBRAND',
      },
    ],
    executiveSummary: 'Cluster A00001 represents a persistent, high-capability cybercrime operator undergoing systematic identity evolution. Multi-source correlation confirms that handles nyxinhex99 and vexatrace belong to the same threat persona, substantiated by uninterrupted financial infrastructure usage (XMR 4b5U...aoX) and distinct NLP stylometric profiles.',
    relationshipFindings: [
      'High-confidence attribution linking operator persona A00001 across underground forum and instant messaging domains.',
      'Cryptocurrency cashout pipeline correlates directly with illicit credential brokering operations.',
      'Infrastructure overlap detected with Cluster A00042 via shared Ethereum smart contract interaction.',
    ],
    behavioralSignals: [
      {
        feature: 'Orthographic Idiosyncrasies',
        similarityScore: 0.94,
        description: 'Consistent habit of omitting final punctuation and using double-hyphen delimiters in technical disclosures.',
      },
      {
        feature: 'Technical Jargon & Tooling',
        similarityScore: 0.89,
        description: 'Recurring terminology referencing specific obfuscation loaders and customized Cobalt Strike malleable C2 profiles.',
      },
      {
        feature: 'Active Temporal Window (UTC)',
        similarityScore: 0.92,
        description: 'Peak operational timestamp clustering strictly between 18:00 UTC and 03:00 UTC across both handles.',
      },
    ],
    infrastructureFindings: [
      'Monero Stealth Address 4b5U...aoX received an estimated 48.2 XMR across 14 darknet escrow settlements.',
      'Ethereum address 0x7e...870 serves as a shared intermediate tumbler with 12 outgoing Tornado Cash deposit hops.',
      'TOR relay fingerprinting identified sequential connection sessions matching Romanian and Dutch exit gateways.',
    ],
    lifecycleAnalysis: 'The target exhibited a deliberate 78-day dormancy protocol between March 2024 and June 2024 following law enforcement takedowns of underground markets. In June 2024, the entity reconstituted operational presence under handle vexatrace without rotating their underlying cryptocurrency cold-storage endpoints.',
    finalAssessment: 'CONFIDENCE LEVEL: CRITICAL / HIGH (92%). The evidentiary convergence across cryptographic wallets, stylometric analysis, and temporal logging confirms a single controlling actor behind Cluster A00001. Escalation to active tactical monitoring and asset freezing is strongly advised.',
  },

  A00042: {
    id: 'A00042',
    clusterId: 'Cluster A00042',
    name: 'Threat Cluster A00042',
    risk: 'high',
    confidence: 0.84,
    threatCategory: 'Exploit Broker / Zero-Day Vulnerability Syndicate',
    firstSeen: '2024-04-10',
    lastActive: '2025-01-29',
    summary: 'Specialized vulnerability trader and exploit development syndicate operating across invite-only hacking portals.',
    handles: ['circuitmoth'],
    wallets: [
      {
        currency: 'ETH',
        address: '0x7e...870',
        fullAddress: '0x7e44a193910F79bA3543164929828d1D35a870',
        role: 'Shared Exploit Settlement Pool',
      },
    ],
    signals: [
      {
        id: 'sig-42-1',
        title: 'WALLET REUSE',
        type: 'WALLET REUSE',
        description: 'Shared ETH address 0x7e...870 with A00001',
        confidence: 0.79,
        severity: 'high',
        details: 'Shared deposit smart contract indicates joint affiliate relationship or common broker intermediary.',
      },
      {
        id: 'sig-42-2',
        title: 'BEHAVIORAL SIGNAL',
        type: 'BEHAVIORAL SIGNAL',
        description: 'High-tier exploit broker dialect',
        confidence: 0.84,
        severity: 'high',
        details: 'Formal Russian-to-English translation syntax typical of Eastern European exploit auction platforms.',
      },
    ],
    timeline: [
      {
        id: 't-42-1',
        date: '2024-08-14',
        title: 'WALLET OVERLAP',
        description: 'Handle circuitmoth shares an ETH wallet previously linked to Cluster A00001 during high-value proof-of-concept auction.',
        confidence: 0.79,
        type: 'WALLET_OVERLAP',
      },
    ],
    executiveSummary: 'Cluster A00042 operates as a specialized vulnerability broker using handle circuitmoth. Financial tracing exposes shared treasury infrastructure with Cluster A00001, implying shared financial conduits or organized criminal partnerships.',
    relationshipFindings: [
      'Controls handle circuitmoth with verified PGP public key signature.',
      'Shares Ethereum address 0x7e...870 with Cluster A00001.',
    ],
    behavioralSignals: [
      {
        feature: 'Cryptographic Signing Protocol',
        similarityScore: 0.88,
        description: 'All public vulnerability advisories signed with specific 4096-bit RSA subkeys.',
      },
    ],
    infrastructureFindings: [
      'Connected to Ethereum cashout endpoint 0x7e...870 with automated split-routing.',
    ],
    lifecycleAnalysis: 'Active trade pattern with periodic burst transactions coinciding with zero-day disclosure cycles.',
    finalAssessment: 'CONFIDENCE LEVEL: HIGH (84%). Direct technical linkage to financial conduits shared with Cluster A00001.',
  },

  A00118: {
    id: 'A00118',
    clusterId: 'Cluster A00118',
    name: 'Threat Cluster A00118',
    risk: 'medium',
    confidence: 0.71,
    threatCategory: 'Low-Volume Darknet Vendor / Ancillary Services',
    firstSeen: '2024-11-05',
    lastActive: '2025-01-09',
    summary: 'Tor directory vendor with disciplined operational security maintaining static Bitcoin cold storage reserves.',
    handles: ['quietledger'],
    wallets: [
      {
        currency: 'BTC',
        address: 'bc1q...9pz',
        fullAddress: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjh4729pz',
        role: 'Legacy Bitcoin Storage',
      },
    ],
    signals: [
      {
        id: 'sig-118-1',
        title: 'LIFECYCLE SIGNAL',
        type: 'LIFECYCLE SIGNAL',
        description: 'Sparse periodic operational bursts',
        confidence: 0.68,
        severity: 'medium',
        details: 'Low-frequency posting schedule designed to minimize digital exhaust and attribution vectors.',
      },
    ],
    timeline: [
      {
        id: 't-118-1',
        date: '2025-01-09',
        title: 'LOW-VOLUME ACTIVITY',
        description: 'Handle quietledger maintains sparse activity with a consistent BTC wallet across vetted Tor hidden services.',
        confidence: 0.68,
        type: 'ACTIVITY',
      },
    ],
    executiveSummary: 'Cluster A00118 represents an auxiliary darknet service provider operating under handle quietledger. Attribution confidence is moderate due to strict OPSEC hygiene.',
    relationshipFindings: [
      'Controls handle quietledger across two verified hidden service markets.',
      'Sole beneficiary of BTC wallet bc1q...9pz.',
    ],
    behavioralSignals: [
      {
        feature: 'OPSEC Discipline',
        similarityScore: 0.76,
        description: 'Strict avoidance of plaintext emails, phone identifiers, or public clearinghouses.',
      },
    ],
    infrastructureFindings: [
      'BTC wallet bc1q...9pz maintains an unspent balance with infrequent consolidation.',
    ],
    lifecycleAnalysis: 'Consistent low-volume baseline without rebranding or infrastructure shifts.',
    finalAssessment: 'CONFIDENCE LEVEL: MEDIUM (71%). Monitored for potential escalation or convergence with larger threat clusters.',
  },
};

export function getGraphData(): GraphData {
  return {
    nodes: JSON.parse(JSON.stringify(MOCK_NODES)),
    links: JSON.parse(JSON.stringify(MOCK_LINKS)),
  };
}

export function getActorProfile(actorId: string): ActorProfile | undefined {
  return MOCK_ACTORS_DATA[actorId];
}

export function getDirectConnections(nodeId: string, graphData: GraphData) {
  const connectedNodeIds = new Set<string>();
  const relevantLinks = graphData.links.filter((link) => {
    const sourceId = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
    const targetId = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
    if (sourceId === nodeId) {
      connectedNodeIds.add(targetId);
      return true;
    }
    if (targetId === nodeId) {
      connectedNodeIds.add(sourceId);
      return true;
    }
    return false;
  });

  const relevantNodes = graphData.nodes.filter((node) => node.id === nodeId || connectedNodeIds.has(node.id));

  return {
    nodes: relevantNodes,
    links: relevantLinks,
    count: connectedNodeIds.size,
  };
}

export function getActorMiniGraphData(actorId: string): GraphData {
  const actor = MOCK_NODES.find((n) => n.id === actorId);
  if (!actor) {
    return { nodes: [], links: [] };
  }

  // Find direct handles
  const handleLinks = MOCK_LINKS.filter((l) => {
    const sourceId = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source;
    return sourceId === actorId && l.type === 'controls';
  });
  const handleIds = new Set(
    handleLinks.map((l) => (typeof l.target === 'object' ? (l.target as GraphNode).id : (l.target as string)))
  );

  // Find wallets connected to those handles
  const walletLinks = MOCK_LINKS.filter((l) => {
    const sourceId = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source;
    return handleIds.has(sourceId);
  });
  const walletIds = new Set(
    walletLinks.map((l) => (typeof l.target === 'object' ? (l.target as GraphNode).id : (l.target as string)))
  );

  const nodes = MOCK_NODES.filter(
    (n) => n.id === actorId || handleIds.has(n.id) || walletIds.has(n.id)
  );
  const links = [...handleLinks, ...walletLinks];

  return {
    nodes: JSON.parse(JSON.stringify(nodes)),
    links: JSON.parse(JSON.stringify(links)),
  };
}
